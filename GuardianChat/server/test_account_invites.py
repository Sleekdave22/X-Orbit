"""Account sign-up link tests; no phone, real accounts or live data involved."""
import concurrent.futures
from pathlib import Path
import sqlite3
import stat
import tempfile
import unittest
from unittest.mock import patch

import account_invites as invites


class Database:
    def __init__(self, data):
        self.data = Path(data)
    def db(self):
        d = sqlite3.connect(self.data / 'test.sqlite', timeout=15)
        d.row_factory = sqlite3.Row
        return d


class AccountInvitesTest(unittest.TestCase):
    A = 'aaaaaaaaaaaa'
    B = 'bbbbbbbbbbbb'
    NOW = 1_800_000_000

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='.account-invites-test-', dir=Path(__file__).parent)
        self.server = Database(self.tmp.name)
        with self.server.db() as d:
            d.execute('CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT)')
            d.executemany('INSERT INTO users VALUES(?,?)', [(self.A, 'Private Alice'), (self.B, 'Private Bob')])
        invites.init(self.server)

    def tearDown(self):
        self.tmp.cleanup()

    def link(self, owner=None, rotate=False):
        return invites.getown(self.server, owner or self.A, rotate=rotate)

    def token(self, owner=None, rotate=False):
        return self.link(owner, rotate)['path'].split('invite=', 1)[1]

    def join(self, number, token, extra=None):
        uid = f'{number:012x}'
        with self.server.db() as d:
            d.execute('BEGIN IMMEDIATE')
            owner = invites.authorize_registration(self.server, d, dict(extra or {}, invite_link=token))
            d.execute('INSERT INTO users VALUES(?,?)', (uid, 'New user'))
            invites.record(d, uid, owner)
        return uid

    def test_private_key_has_correct_length_permissions_and_survives_restart(self):
        path = self.server.data / 'account-invites.key'
        self.assertEqual(len(path.read_bytes()), 32)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        token = self.token()
        restarted = Database(self.tmp.name)
        invites.init(restarted)
        self.assertEqual(restarted.account_invite_key, self.server.account_invite_key)
        self.assertEqual(invites.validatepublic(restarted, token), {'valid': True})
        self.assertEqual(invites.getown(restarted, self.A), self.link())
        path.chmod(0o644)
        repaired = Database(self.tmp.name); invites.init(repaired)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_issuance_is_account_owned_unique_and_public_response_is_minimal(self):
        a, b = self.link(self.A), self.link(self.B)
        self.assertNotEqual(a['path'], b['path'])
        self.assertEqual(set(a), {'path', 'created', 'joined'})
        self.assertEqual(a['joined'], 0)
        self.assertEqual(self.link(self.A), a)
        self.assertEqual(invites.validatepublic(self.server, self.token(self.A)), {'valid': True})
        for bad in ('', 'unknown-user', 'cccccccccccc', {'owner': self.A}, None):
            with self.assertRaises(PermissionError): invites.getown(self.server, bad)
        with self.assertRaises(ValueError): invites.getown(self.server, self.A, rotate='true')

    def test_database_contains_nonce_not_complete_token_or_signing_key(self):
        token = self.token()
        with self.server.db() as d:
            record = dict(d.execute('SELECT * FROM account_invites').fetchone())
            self.assertEqual(set(record), {'owner', 'nonce', 'created'})
            self.assertEqual(record['nonce'], token.split('.')[1])
            self.assertNotIn(token, str(record))
            self.assertNotIn(self.server.account_invite_key.hex(), str(record))

    def test_rotation_revokes_old_link_without_resetting_join_count(self):
        old = self.token(); self.join(1, old)
        rotated = self.link(rotate=True); new = rotated['path'].split('invite=', 1)[1]
        self.assertNotEqual(old, new)
        self.assertEqual(rotated['joined'], 1)
        self.assertEqual(invites.validatepublic(self.server, new), {'valid': True})
        with self.assertRaisesRegex(PermissionError, invites.INVALID): invites.validatepublic(self.server, old)
        with self.server.db() as d:
            d.execute('BEGIN IMMEDIATE')
            with self.assertRaises(ValueError): invites.authorize_registration(self.server, d, {'invite_link': old})

    def test_forgery_malformed_tokens_and_deleted_owners_are_generic(self):
        token = self.token(); owner, nonce, mac = token.split('.')
        invalid = [self.B + '.' + nonce + '.' + mac, owner + '.A' + nonce[1:] + '.' + mac,
                   owner + '.' + nonce + '.A' + mac[1:], token + '.extra', token + '\n',
                   'x' * 10000, '', None, {}, [], 123]
        # Avoid a one-in-sixty-four accidental unchanged mutation.
        invalid[1] = owner + '.' + ('B' if nonce[0] == 'A' else 'A') + nonce[1:] + '.' + mac
        invalid[2] = owner + '.' + nonce + '.' + ('B' if mac[0] == 'A' else 'A') + mac[1:]
        for bad in invalid:
            with self.assertRaises(PermissionError) as error: invites.validatepublic(self.server, bad)
            self.assertEqual(str(error.exception), invites.INVALID)
        with self.server.db() as d: d.execute('DELETE FROM users WHERE id=?', (self.A,))
        with self.assertRaisesRegex(PermissionError, invites.INVALID): invites.validatepublic(self.server, token)

    def test_registration_uses_signed_owner_ignores_supplied_attribution(self):
        token = self.token()
        self.join(1, token, {'owner': self.B, 'inviter': self.B})
        self.assertEqual(self.link(self.A)['joined'], 1)
        self.assertEqual(self.link(self.B)['joined'], 0)
        with self.server.db() as d:
            self.assertEqual(d.execute('SELECT owner FROM account_invite_joins').fetchone()['owner'], self.A)
            self.assertIsNone(invites.authorize_registration(self.server, d, {'invite': 'legacy-code', 'owner': self.B}))
            invites.record(d, '000000000001', self.A)
            self.assertEqual(d.execute('SELECT COUNT(*) FROM account_invite_joins').fetchone()[0], 1)
            with self.assertRaises(ValueError): invites.record(d, '000000000001', self.B)

    def test_invalid_bodies_fail_as_values_before_sql_and_legacy_path_is_preserved(self):
        class NoSQL:
            def execute(self, *_args):
                raise AssertionError('Malformed sign-up details must not reach SQL')
        for body in (None, [], '', 1, {'invite_link': None}, {'invite_link': {}}, {'invite_link': ''}, {'invite_link': 'bad'}):
            with self.assertRaises(ValueError): invites.authorize_registration(self.server, NoSQL(), body)
        self.assertIsNone(invites.authorize_registration(self.server, NoSQL(), {}))
        self.assertIsNone(invites.authorize_registration(self.server, NoSQL(), {'invite': 'legacy'}))

    def test_getown_concurrent_requests_are_idempotent(self):
        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            links = list(pool.map(lambda _: self.link()['path'], range(20)))
        self.assertEqual(len(set(links)), 1)
        with self.server.db() as d:
            self.assertEqual(d.execute('SELECT COUNT(*) FROM account_invites').fetchone()[0], 1)

    def test_twenty_join_hourly_limit_is_atomic_under_concurrent_registration(self):
        token = self.token()
        def attempt(number):
            try:
                self.join(number, token)
                return True
            except ValueError as e:
                self.assertIn('temporary registration limit', str(e))
                return False
        with patch('account_invites.time.time', return_value=self.NOW):
            with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
                outcomes = list(pool.map(attempt, range(1, 31)))
        self.assertEqual(sum(outcomes), 20)
        self.assertEqual(self.link()['joined'], 20)
        with self.server.db() as d:
            self.assertEqual(d.execute('SELECT COUNT(*) FROM users').fetchone()[0], 22)

    def test_daily_limit_and_rotation_do_not_allow_rate_bypass(self):
        token = self.token()
        with self.server.db() as d:
            for number in range(1, 101):
                uid = f'{number:012x}'
                d.execute('INSERT INTO account_invite_joins VALUES(?,?,?)', (uid, self.A, self.NOW - 7200))
        with patch('account_invites.time.time', return_value=self.NOW):
            new = self.token(rotate=True)
            with self.assertRaisesRegex(ValueError, 'temporary registration limit'): self.join(101, new)
        # Old attribution remains for counters but stops counting toward rate limits.
        with patch('account_invites.time.time', return_value=self.NOW + 86401):
            self.join(101, new)
        self.assertEqual(self.link()['joined'], 101)

    def test_failed_signup_rolls_back_attribution_and_account(self):
        token = self.token(); uid = '000000000001'
        with self.assertRaises(RuntimeError):
            with self.server.db() as d:
                d.execute('BEGIN IMMEDIATE')
                owner = invites.authorize_registration(self.server, d, {'invite_link': token})
                d.execute('INSERT INTO users VALUES(?,?)', (uid, 'New user'))
                invites.record(d, uid, owner)
                raise RuntimeError('Simulated password/session persistence failure')
        with self.server.db() as d:
            self.assertFalse(d.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone())
        self.assertEqual(self.link()['joined'], 0)

    def test_bad_existing_key_is_not_silently_regenerated(self):
        path = self.server.data / 'account-invites.key'; path.write_bytes(b'broken')
        with self.assertRaises(RuntimeError): invites.init(Database(self.tmp.name))
        self.assertEqual(path.read_bytes(), b'broken')


if __name__ == '__main__':
    unittest.main()
