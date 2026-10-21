"""Revocable account-owned sign-up links, separate from contacts and matches.

The signing key stays in the private server data directory. The database stores
only each account's current random nonce, never a complete invitation capability.
Registration authorization and attribution run inside the caller's existing
BEGIN IMMEDIATE transaction so concurrent sign-ups cannot bypass join limits.
"""
import base64
import hashlib
import hmac
import os
from pathlib import Path
import re
import secrets
import stat
import time

ACCOUNT = re.compile(r'[0-9a-f]{12}')
TOKEN = re.compile(r'([0-9a-f]{12})\.([A-Za-z0-9_-]{24})\.([A-Za-z0-9_-]{43})')
INVALID = 'This sign-up invitation is invalid or has been replaced'
HOURLY_JOINS = 20
DAILY_JOINS = 100


def _load_key(data):
    path = Path(data) / 'account-invites.key'
    nofollow = getattr(os, 'O_NOFOLLOW', 0)
    try:
        fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | nofollow, 0o600)
    except FileExistsError:
        pass
    else:
        try:
            key = secrets.token_bytes(32)
            with os.fdopen(fd, 'wb') as f:
                f.write(key)
                f.flush()
                os.fsync(f.fileno())
        except BaseException:
            path.unlink(missing_ok=True)
            raise
    fd = os.open(path, os.O_RDONLY | nofollow)
    with os.fdopen(fd, 'rb') as f:
        if not stat.S_ISREG(os.fstat(f.fileno()).st_mode):
            raise RuntimeError('Account invitation key must be a private regular file')
        os.fchmod(f.fileno(), 0o600)
        key = f.read(33)
    if len(key) != 32:
        raise RuntimeError('Account invitation signing key is invalid; preserve it for recovery')
    return key


def init(server):
    if not hasattr(server, 'account_invite_key'):
        server.account_invite_key = _load_key(server.data)
    with server.db() as d:
        d.executescript('''
        CREATE TABLE IF NOT EXISTS account_invites(
            owner TEXT PRIMARY KEY, nonce TEXT NOT NULL UNIQUE, created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS account_invite_joins(
            uid TEXT PRIMARY KEY, owner TEXT NOT NULL, created INTEGER NOT NULL);
        CREATE INDEX IF NOT EXISTS account_invite_join_owner_time
            ON account_invite_joins(owner,created);
        ''')


def _account(d, uid):
    if (not isinstance(uid, str) or not ACCOUNT.fullmatch(uid)
            or not d.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone()):
        raise PermissionError('Sign in to manage your sign-up invitation')


def _mac(server, owner, nonce):
    message = (owner + '.' + nonce).encode('ascii')
    digest = hmac.new(server.account_invite_key, message, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode('ascii').rstrip('=')


def _owner(server, d, token):
    parsed = TOKEN.fullmatch(token) if isinstance(token, str) and len(token) <= 128 else None
    if not parsed:
        raise PermissionError(INVALID)
    owner, nonce, signature = parsed.groups()
    if not hmac.compare_digest(_mac(server, owner, nonce), signature):
        raise PermissionError(INVALID)
    saved = d.execute('''SELECT i.nonce FROM account_invites i JOIN users u ON u.id=i.owner
                         WHERE i.owner=?''', (owner,)).fetchone()
    if not saved or not hmac.compare_digest(saved['nonce'], nonce):
        raise PermissionError(INVALID)
    return owner


def getown(server, uid, rotate=False):
    """uid must come from the authenticated session, never a supplied owner field."""
    if type(rotate) is not bool:
        raise ValueError('Choose whether to replace your existing sign-up link')
    with server.db() as d:
        d.execute('BEGIN IMMEDIATE')
        _account(d, uid)
        saved = d.execute('SELECT nonce,created FROM account_invites WHERE owner=?', (uid,)).fetchone()
        if not saved or rotate:
            nonce = secrets.token_urlsafe(18)
            created = int(time.time())
            d.execute('''INSERT INTO account_invites VALUES(?,?,?)
                         ON CONFLICT(owner) DO UPDATE SET nonce=excluded.nonce,created=excluded.created''',
                      (uid, nonce, created))
        else:
            nonce, created = saved['nonce'], saved['created']
        joined = d.execute('SELECT COUNT(*) FROM account_invite_joins WHERE owner=?', (uid,)).fetchone()[0]
        token = uid + '.' + nonce + '.' + _mac(server, uid, nonce)
        return {'path': '/join?invite=' + token, 'created': created, 'joined': joined}


def validatepublic(server, token):
    with server.db() as d:
        _owner(server, d, token)
    return {'valid': True}


def authorize_registration(server, d, body):
    """Validate under the registration write transaction; return trusted owner only."""
    if type(body) is not dict:
        raise ValueError('Enter valid sign-up details')
    if 'invite_link' not in body:
        return None
    try:
        owner = _owner(server, d, body['invite_link'])
    except PermissionError:
        raise ValueError(INVALID) from None
    now = int(time.time())
    counts = d.execute('''SELECT COUNT(*) daily,
                         COALESCE(SUM(CASE WHEN created>=? THEN 1 ELSE 0 END),0) hourly
                         FROM account_invite_joins WHERE owner=? AND created>=?''',
                       (now - 3600, owner, now - 86400)).fetchone()
    if counts['hourly'] >= HOURLY_JOINS or counts['daily'] >= DAILY_JOINS:
        raise ValueError('This sign-up invitation has reached its temporary registration limit; please try again later')
    return owner


def record(d, uid, owner):
    if owner is None:
        return
    if (not isinstance(uid, str) or not ACCOUNT.fullmatch(uid)
            or not isinstance(owner, str) or not ACCOUNT.fullmatch(owner) or uid == owner):
        raise ValueError('Invalid sign-up invitation attribution')
    if not d.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
        raise ValueError('Create the account before recording its sign-up invitation')
    if not d.execute('SELECT 1 FROM users WHERE id=?', (owner,)).fetchone():
        raise ValueError(INVALID)
    existing = d.execute('SELECT owner FROM account_invite_joins WHERE uid=?', (uid,)).fetchone()
    if existing:
        if existing['owner'] != owner:
            raise ValueError('This account already has a recorded sign-up invitation')
        return
    d.execute('INSERT INTO account_invite_joins VALUES(?,?,?)', (uid, owner, int(time.time())))
