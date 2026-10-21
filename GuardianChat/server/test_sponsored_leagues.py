import concurrent.futures
import json
import sqlite3
import time
import unittest
import urllib.error
from unittest.mock import patch

import sponsored_leagues
import test_server


class SponsoredLeagueTest(unittest.TestCase):
    call = test_server.ChatTest.call
    register = test_server.ChatTest.register

    def setUp(self):
        self.clock = int(time.time())
        self.time_patch = patch("time.time", side_effect=lambda: self.clock)
        self.time_patch.start()
        self.addCleanup(self.time_patch.stop)
        test_server.ChatTest.setUp(self)
        self.players = [self.register(name) for name in ("Owner", "Alice", "Bob", "Charlie")]
        with self.server.db() as d:
            d.execute("INSERT INTO game_admin VALUES(?)", (self.players[0]["id"],))
        for user in self.players:
            self.call("/gaming/profile", {"tag": user["name"], "game_id": user["id"], "adult": True}, user["token"])
            self.call("/identities/save", {"game": "efootball", "game_id": "game-" + user["id"],
                      "region": "Nigeria", "tz": "Africa/Lagos", "availability": [],
                      "platform": "mobile", "country": "NG"}, user["token"])

    tearDown = test_server.ChatTest.tearDown

    def league(self, participants=None):
        owner = self.players[0]
        body = dict(name="Open sponsor league", description="Open entry", sponsor="GuardianLab",
                    sponsor_url="", prize="Recognition only; no automated prize settlement",
                    game="efootball", platform="mobile", registration_opens=self.clock - 1,
                    registration_closes=self.clock + 10, starts=self.clock + 20,
                    ends=self.clock + 200, capacity=100000)
        lid = self.call("/leagues/create", body, owner["token"])["league"]
        self.call("/leagues/transition", dict(league=lid, version=1, state="PUBLISHED", reason="Publish approved rules"), owner["token"])
        for user in self.players[1:3] if participants is None else participants:
            self.call("/leagues/register", {"league": lid}, user["token"])
        return lid

    def activate(self):
        self.clock += 21
        sponsored_leagues.tick(self.server, self.clock)
        sponsored_leagues.tick(self.server, self.clock)

    def search(self, lid, players=None):
        a, b = players or self.players[1:3]
        self.call("/leagues/queue", {"league": lid}, a["token"])
        mid = self.call("/leagues/queue", {"league": lid}, b["token"])["match"]
        self.assertTrue(mid)
        return mid

    def finish(self, mid, league=True, disagree=False):
        with self.server.db() as d:
            match = dict(d.execute("SELECT * FROM gb_matches WHERE id=?", (mid,)).fetchone())
        users = {u["id"]: u for u in self.players}
        prefix = "/leagues/" if league else "/gamebox/"
        for action in ("accept", "checkin"):
            for uid in (match["a"], match["b"]):
                self.call(prefix + action, {"match": mid}, users[uid]["token"])
        self.call(prefix + "complete", {"match": mid}, users[match["a"]]["token"])
        self.call(prefix + "report", {"match": mid, "a": 2, "b": 1}, users[match["a"]]["token"])
        self.call(prefix + "report", {"match": mid, "a": 0 if disagree else 2, "b": 1}, users[match["b"]]["token"])
        return match

    def test_league_points_are_once_only_and_global_rating_is_unchanged(self):
        lid = self.league()
        self.activate()
        mid = self.search(lid)
        match = self.finish(mid)
        self.call("/leagues/report", {"match": mid, "a": 2, "b": 1}, self.players[1]["token"])
        with self.server.db() as d:
            self.assertEqual(d.execute("SELECT count(*) FROM gb_ratings").fetchone()[0], 0)
            self.assertEqual(d.execute("SELECT count(*) FROM gb_rank_awards").fetchone()[0], 0)
            self.assertEqual(d.execute("SELECT count(*) FROM sl_results").fetchone()[0], 1)
            self.assertEqual(d.execute("SELECT points FROM sl_standings WHERE league=? AND uid=?", (lid, match["a"])).fetchone()[0], 3)
            self.assertEqual(d.execute("SELECT count(*) FROM gb_player_reservations").fetchone()[0], 0)
            self.assertEqual(d.execute("SELECT rated FROM gb_matches WHERE id=?", (mid,)).fetchone()[0], 0)
        exhausted = self.call("/leagues/queue", {"league": lid}, self.players[1]["token"])
        self.assertEqual(exhausted["state"], "exhausted")

    def test_global_match_changes_only_global_rating(self):
        lid = self.league()
        a, b = self.players[1:3]
        self.call("/gamebox/queue", {"game": "efootball"}, a["token"])
        mid = self.call("/gamebox/queue", {"game": "efootball"}, b["token"])["match"]
        self.finish(mid, league=False)
        with self.server.db() as d:
            self.assertEqual(d.execute("SELECT count(*) FROM gb_rank_awards").fetchone()[0], 1)
            self.assertEqual(d.execute("SELECT sum(points) FROM sl_standings WHERE league=?", (lid,)).fetchone()[0], 0)
            self.assertEqual(d.execute("SELECT count(*) FROM sl_results").fetchone()[0], 0)

    def test_void_appeal_requires_independent_review_and_reserves_both_players(self):
        lid=self.league();self.activate();mid=self.search(lid)
        self.call('/leagues/decline',{'match':mid},self.players[1]['token'])
        self.call('/leagues/appeal',{'match':mid,'league':lid,'reason':'Opponent cancelled before we could check in'},self.players[1]['token'])
        with self.assertRaises(urllib.error.HTTPError):
            self.call('/leagues/appeal_decide',{'match':mid,'league':lid,'player':self.players[1]['id'],'decision':'reopen_review','reason':'I cannot review my own result'},self.players[1]['token'])
        self.call('/leagues/appeal_decide',{'match':mid,'league':lid,'player':self.players[1]['id'],'decision':'reopen_review','reason':'Independent evidence needs another review'},self.players[0]['token'])
        with self.server.db() as d:
            self.assertEqual(d.execute('select count(*) from gb_player_reservations where match=?',(mid,)).fetchone()[0],2)
            self.assertEqual(d.execute('select count(*) from sl_results').fetchone()[0],0)
        self.assertEqual(self.call('/leagues/appeals',token=self.players[0]['token'])['appeals'],[])
        self.call('/leagues/resolve_void',{'match':mid,'league':lid,'reason':'Evidence cannot establish a completed match'},self.players[0]['token'])
        with self.server.db() as d:self.assertEqual(d.execute('select count(*) from gb_player_reservations').fetchone()[0],0)

    def test_disagreement_is_held_and_review_timeout_releases_without_points(self):
        lid = self.league()
        self.activate()
        mid = self.search(lid)
        self.finish(mid, disagree=True)
        with self.server.db() as d:
            self.assertEqual(d.execute("SELECT state FROM gb_matches WHERE id=?", (mid,)).fetchone()[0], "disputed")
            self.assertEqual(d.execute("SELECT count(*) FROM sl_results").fetchone()[0], 0)
            deadline = d.execute("SELECT deadline FROM gb_matches WHERE id=?", (mid,)).fetchone()[0]
        self.clock = deadline + 172801
        sponsored_leagues.tick(self.server, self.clock)
        with self.server.db() as d:
            self.assertEqual(d.execute("SELECT state FROM gb_matches WHERE id=?", (mid,)).fetchone()[0], "cancelled")
            self.assertEqual(d.execute("SELECT count(*) FROM gb_player_reservations").fetchone()[0], 0)
            self.assertEqual(d.execute("SELECT count(*) FROM sl_results").fetchone()[0], 0)

    def test_league_pairing_ignores_global_rating_and_cancel_continues_search(self):
        lid = self.league(self.players[1:])
        with self.server.db() as d:
            for index, user in enumerate(self.players[1:]):
                d.execute("INSERT INTO gb_ratings(uid,game,rating) VALUES(?,'efootball',?)", (user["id"], 100 + index * 3000))
        self.activate()
        mid = self.search(lid)
        self.call("/leagues/decline", {"match": mid}, self.players[2]["token"])
        with self.server.db() as d:
            self.assertTrue(d.execute("SELECT 1 FROM sl_queue WHERE uid=?", (self.players[1]["id"],)).fetchone())
        result = self.call("/leagues/queue", {"league": lid}, self.players[3]["token"])
        self.assertTrue(result["match"])
        self.assertNotEqual(mid, result["match"])

    def test_singleton_and_origins_are_database_enforced(self):
        lid = self.league()
        other = self.league([])
        with self.server.db() as d:
            d.execute("UPDATE sl_leagues SET state='ACTIVE' WHERE id=?", (lid,))
            with self.assertRaises(sqlite3.IntegrityError):
                d.execute("UPDATE sl_leagues SET state='ACTIVE' WHERE id=?", (other,))
        self.clock += 21
        mid = self.search(lid)
        with self.server.db() as d:
            with self.assertRaises(sqlite3.IntegrityError):
                d.execute("UPDATE gb_match_origins SET global_ranking_eligible=1 WHERE match=?", (mid,))
            with self.assertRaises(sqlite3.IntegrityError):
                d.execute("UPDATE gb_matches SET a=b WHERE id=?", (mid,))

    def test_concurrent_requests_cannot_double_assign(self):
        lid = self.league(self.players[1:])
        self.activate()
        self.call("/leagues/queue", {"league": lid}, self.players[1]["token"])
        def join(user):
            return self.call("/leagues/queue", {"league": lid}, user["token"])
        with concurrent.futures.ThreadPoolExecutor(2) as executor:
            results = list(executor.map(join, self.players[2:]))
        self.assertEqual(sum(bool(result["match"]) for result in results), 1)
        with self.server.db() as d:
            self.assertEqual(d.execute("SELECT count(*) FROM gb_player_reservations").fetchone()[0], 2)

    def test_registration_deadline_and_cancelled_search(self):
        lid = self.league()
        with self.assertRaises(urllib.error.HTTPError):
            self.call("/leagues/queue", {"league": lid}, self.players[1]["token"])
        self.activate()
        with self.assertRaises(urllib.error.HTTPError):
            self.call("/leagues/register", {"league": lid}, self.players[3]["token"])
        self.call("/leagues/queue", {"league": lid}, self.players[1]["token"])
        self.call("/leagues/queue_leave", {"league": lid}, self.players[1]["token"])
        self.assertEqual(self.call("/leagues/queue", {"league": lid}, self.players[2]["token"])["state"], "searching")


if __name__ == "__main__":
    unittest.main()
