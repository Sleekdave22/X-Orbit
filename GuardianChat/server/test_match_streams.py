"""Real SQLite transactions with a deterministic media-ready relay boundary."""
import concurrent.futures
import json
from pathlib import Path
import sqlite3
import tempfile
import time
import unittest

import gaming
import live_reactions
import match_streams
import social
import stream_lifecycle as life


class FakeRelay:
    enabled = True
    def __init__(self):
        self.live = set(); self.ended = []
    def ready(self, rid):
        return rid in self.live
    def end_room(self, rid):
        self.live.discard(rid); self.ended.append(rid)


class Database:
    def __init__(self, data):
        self.data = Path(data); self.stream_relay = FakeRelay()
    def db(self):
        d = sqlite3.connect(self.data / 'test.sqlite', timeout=15)
        d.row_factory = sqlite3.Row
        return d


class MatchStreamsTest(unittest.TestCase):
    def setUp(self):
        # Explicit local directory also runs in a restricted test environment.
        self.tmp = tempfile.TemporaryDirectory(prefix='.match-stream-test-', dir=Path(__file__).parent)
        self.s = Database(self.tmp.name); self.now = int(time.time())
        with self.s.db() as d:
            d.execute('CREATE TABLE users(id TEXT PRIMARY KEY,name TEXT,nickname TEXT,avatar TEXT,avatar_mime TEXT)')
            for n in range(25):
                uid = 'u' + str(n)
                d.execute('INSERT INTO users VALUES(?,?,?,?,?)', (uid, 'Player ' + str(n), uid, 'picture-' + uid, 'image/png'))
        social.init(self.s); gaming.init(self.s); life.init(self.s)
        with self.s.db() as d:
            for n in range(25):
                uid = 'u' + str(n)
                d.execute('INSERT INTO game_profiles VALUES(?,?,?,?,?,?)', (uid, uid, 'secret-' + uid, '@social-' + uid, int(n == 0), 1))
            d.execute("INSERT INTO gb_matches(id,game,a,b,gid_a,gid_b,state,created,deadline,rules) VALUES('match','efootball','u0','u1','private-a','private-b','in_progress',?,?,?)", (self.now, self.now + 7200, '{}'))
            d.execute("INSERT INTO leagues(id,name,game,owner,state,created) VALUES('league','Competition','efootball','u0','active',?)", (self.now,))
            d.execute("INSERT INTO fixtures(id,league,a,b,opens,due,state) VALUES('fixture','league','u0','u1',?,?,'scheduled')", (self.now - 60, self.now + 3600))

    def tearDown(self):
        self.tmp.cleanup()

    def create(self, uid='u0', kind='open', mid='match'):
        return match_streams.create(self.s, uid, {'kind': kind, 'match': mid})

    def start(self):
        r = self.create(); self.rid = r['id']
        gaming.post(self.s, 'u0', 'stream_begin', {'room': self.rid})
        self.s.stream_relay.live.add(self.rid)
        return r

    def test_create_is_participant_only_and_idempotent_under_concurrency(self):
        with self.assertRaises(PermissionError): self.create('u2')
        with concurrent.futures.ThreadPoolExecutor(max_workers=6) as pool:
            rooms = list(pool.map(lambda _: self.create()['id'], range(12)))
        self.assertEqual(len(set(rooms)), 1)
        second_host = self.create('u1')
        self.assertNotEqual(second_host['id'], rooms[0])
        with self.s.db() as d:
            self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_links').fetchone()[0], 2)

    def test_directory_requires_actual_video_and_never_exposes_private_rooms(self):
        r = self.create(); rid = r['id']
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])
        gaming.post(self.s, 'u0', 'stream_begin', {'room': rid})
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])
        with self.assertRaises(PermissionError): match_streams.join(self.s, 'u2', rid)
        self.s.stream_relay.live.add(rid)
        with self.s.db() as d:
            d.execute('INSERT INTO game_stream_rooms VALUES(?,?,?,?)', ('private', 'u0', 'u1', self.now))
            life.begin(d, 'u0', 'private')
        self.s.stream_relay.live.add('private')
        rooms = match_streams.list_streams(self.s, 'u2')['streams']
        self.assertEqual([r['id'] for r in rooms], [rid])
        self.assertEqual(rooms[0]['media'], 'relay')
        self.assertTrue(rooms[0]['broadcasting'])
        with self.s.db() as d: d.execute('UPDATE live_sessions SET heartbeat=0 WHERE room=?', (rid,))
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])

    def test_twenty_viewers_can_join_but_cannot_publish(self):
        r = self.start()
        for n in range(2, 22):
            uid = 'u' + str(n)
            joined = match_streams.join(self.s, uid, r['id'])
            self.assertEqual(joined['invitation'], 'accepted')
            self.assertFalse(joined['can_broadcast'])
            self.assertEqual(match_streams.authorize(self.s, uid, r['id'])['id'], r['id'])
            gaming.post(self.s, uid, 'stream_watch', {'room': r['id']})
        with self.s.db() as d:
            self.assertEqual(life.state(d, r['id'])['viewers'], 20)
        with self.assertRaises(PermissionError): match_streams.authorize(self.s, 'u2', r['id'], publish=True)
        with self.assertRaises(PermissionError): match_streams.join(self.s, 'missing-account', r['id'])

    def test_blocks_revoke_discovery_join_media_and_comments(self):
        r = self.start(); match_streams.join(self.s, 'u2', r['id'])
        with self.s.db() as d: d.execute('INSERT INTO social_blocks VALUES(?,?)', ('u1', 'u2'))
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])
        with self.assertRaises(PermissionError): match_streams.join(self.s, 'u2', r['id'])
        with self.assertRaises(PermissionError): match_streams.authorize(self.s, 'u2', r['id'])
        with self.assertRaises(PermissionError): gaming.post(self.s, 'u2', 'stream_comment', {'room': r['id'], 'text': 'Blocked'})
        with self.assertRaises(PermissionError): gaming.stream_signals(self.s, 'u2', r['id'])

    def test_public_metadata_has_no_game_ids_scores_sdp_or_session_tokens(self):
        self.start()
        r = match_streams.list_streams(self.s, 'u2')['streams'][0]
        text = json.dumps(r)
        for secret in ('private-a', 'private-b', 'secret-u0', 'secret-u1', 'score_a', 'score_b', 'sid', 'token', 'sdp'):
            self.assertNotIn(secret, text)
        self.assertEqual(r['players'][0]['avatar'], 'picture-u0')
        self.assertEqual(r['players'][1]['avatar'], '')
        self.assertEqual(r['share_path'], '/gaming.html?stream=' + r['id'])
        self.assertEqual(r['match'], {'kind': 'open', 'id': 'match', 'game': 'efootball', 'state': 'in_progress', 'context': 'Open match'})

    def test_fixture_window_and_terminal_match_states(self):
        r = self.create(kind='fixture', mid='fixture')
        self.assertEqual(r['match']['kind'], 'fixture')
        with self.s.db() as d: d.execute('UPDATE fixtures SET opens=? WHERE id=?', (self.now + 3600, 'fixture'))
        with self.assertRaises(PermissionError): self.create(kind='fixture', mid='fixture')
        for state in ('proposed', 'verified', 'cancelled', 'disputed', 'review'):
            with self.s.db() as d: d.execute('UPDATE gb_matches SET state=? WHERE id=?', (state, 'match'))
            with self.assertRaises(PermissionError): self.create()

    def test_own_pending_room_metadata_is_relay_but_not_an_opponent_invitation(self):
        r = self.create()
        own = gaming.summary(self.s, 'u0')['stream_rooms']
        self.assertEqual(len(own), 1)
        self.assertEqual(own[0]['media'], 'relay')
        self.assertFalse(own[0]['broadcasting'])
        self.assertEqual(gaming.summary(self.s, 'u1')['stream_rooms'], [])
        with self.assertRaises(PermissionError): match_streams.authorize(self.s, 'u1', r['id'])

    def test_host_eligibility_errors_roll_back_room_creation(self):
        with self.s.db() as d: d.execute("UPDATE game_profiles SET adult=0 WHERE uid='u0'")
        with self.assertRaises(PermissionError): self.create()
        with self.s.db() as d:
            self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_rooms').fetchone()[0], 0)
            d.execute("UPDATE game_profiles SET adult=1 WHERE uid='u0'")
            d.execute('INSERT INTO gb_sanctions VALUES(?,?,?,?)', ('u0', 'efootball', self.now + 3600, 'Active restriction'))
        with self.assertRaises(PermissionError): self.create()
        with self.s.db() as d: self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_rooms').fetchone()[0], 0)

    def test_unavailable_relay_is_explicit_and_has_no_mesh_fallback(self):
        self.s.stream_relay.enabled = False
        with self.assertRaisesRegex(ValueError, 'temporarily unavailable'): self.create()
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])
        with self.s.db() as d: self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_rooms').fetchone()[0], 0)

    def test_session_end_purges_interactions_and_counts_each_viewer_once(self):
        r = self.start(); rid = r['id']; match_streams.join(self.s, 'u2', rid)
        for _ in range(3): gaming.post(self.s, 'u2', 'stream_watch', {'room': rid})
        gaming.post(self.s, 'u2', 'stream_comment', {'room': rid, 'text': 'Ephemeral'})
        gaming.post(self.s, 'u2', 'stream_like', {'room': rid})
        live_reactions.emit(rid, 'u2', '❤️')
        gaming.post(self.s, 'u0', 'stream_end', {'room': rid})
        gaming.post(self.s, 'u0', 'stream_end', {'room': rid})
        with self.s.db() as d:
            self.assertEqual(life.total(d, 'u0'), 1)
            for table in ('game_stream_links', 'game_stream_transport', 'game_stream_rooms', 'game_stream_comments', 'game_stream_likes', 'game_stream_signals', 'game_stream_members', 'game_stream_responses', 'live_viewers', 'live_sessions'):
                self.assertEqual(d.execute('SELECT COUNT(*) FROM ' + table).fetchone()[0], 0)
        self.assertEqual(live_reactions.read(rid), [])
        self.assertEqual(self.s.stream_relay.ended, [rid])
        with self.assertRaises(PermissionError): match_streams.join(self.s, 'u2', rid)

    def test_legacy_private_access_remains_invitation_only_and_relay_invites_have_no_cap(self):
        with self.s.db() as d: d.execute('INSERT INTO game_admin VALUES(?)', ('u0',))
        r = gaming.post(self.s, 'u0', 'stream_create', {'identity': 'u1'})
        with self.assertRaises(PermissionError): match_streams.join(self.s, 'u2', r['id'])
        with self.assertRaises(PermissionError): gaming.stream_signals(self.s, 'u1', r['id'])
        gaming.post(self.s, 'u1', 'stream_accept', {'room': r['id']})
        for n in range(2, 12):
            gaming.post(self.s, 'u0', 'stream_invite', {'room': r['id'], 'identity': 'u' + str(n)})
        with self.s.db() as d:
            self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_members WHERE room=?', (r['id'],)).fetchone()[0], 10)
            self.assertEqual(match_streams.describe(d, self.s, 'u1', d.execute('SELECT * FROM game_stream_rooms WHERE id=?', (r['id'],)).fetchone())['media'], 'relay')

    def test_match_closure_expires_room_and_preserves_aggregate(self):
        r = self.start(); match_streams.join(self.s, 'u2', r['id'])
        gaming.post(self.s, 'u2', 'stream_watch', {'room': r['id']})
        with self.s.db() as d: d.execute("UPDATE gb_matches SET state='verified' WHERE id='match'")
        self.assertEqual(match_streams.list_streams(self.s, 'u2')['streams'], [])
        life.expire(self.s)
        with self.s.db() as d:
            self.assertEqual(life.total(d, 'u0'), 1)
            self.assertEqual(d.execute('SELECT COUNT(*) FROM game_stream_links').fetchone()[0], 0)


if __name__ == '__main__':
    unittest.main()
