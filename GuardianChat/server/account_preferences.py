"""A user's visual preferences, separate from administrator-published themes."""
import json
import time
from pathlib import Path

PALETTES = json.loads(Path(__file__).with_name('personalization.json').read_text())
DEFAULT = 'oxblood-gold'

def canonical(value):
    return next((p['id'] for p in PALETTES if value == p['id'] or value in p.get('aliases', [])), None)

def init(server):
    with server.db() as db:
        db.execute('CREATE TABLE IF NOT EXISTS account_preferences(uid TEXT PRIMARY KEY REFERENCES users(id),palette TEXT NOT NULL,updated INTEGER NOT NULL)')

def get(server, uid):
    with server.db() as db:
        row = db.execute('SELECT palette FROM account_preferences WHERE uid=?', (uid,)).fetchone()
    return {'palette': (canonical(row['palette']) if row else None) or DEFAULT, 'choices': PALETTES}

def save(server, uid, body):
    if set(body) != {'palette'} or not isinstance(body['palette'], str) or canonical(body['palette']) is None:
        raise ValueError('Choose an available colour')
    with server.db() as db:
        db.execute('INSERT INTO account_preferences VALUES(?,?,?) ON CONFLICT(uid) DO UPDATE SET palette=excluded.palette,updated=excluded.updated', (uid,canonical(body['palette']),int(time.time())))
    return get(server, uid)
