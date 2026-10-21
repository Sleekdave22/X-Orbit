"""Immutable origins and shared player reservations for the existing match engine."""
import time

TERMINAL = ("verified", "cancelled")


def init(server):
    from sponsored_leagues import schema
    with server.db() as d:
        schema(d)
        d.executescript("""
        CREATE TABLE IF NOT EXISTS gb_competition_migrations(version INTEGER PRIMARY KEY,created INTEGER);
        CREATE TABLE IF NOT EXISTS gb_match_origins(
          match TEXT PRIMARY KEY REFERENCES gb_matches(id) DEFERRABLE INITIALLY DEFERRED,
          match_type TEXT NOT NULL CHECK(match_type IN ('GLOBAL_RANKED','SPONSORED_LEAGUE')),
          league_id TEXT REFERENCES sl_leagues(id), global_ranking_eligible INTEGER NOT NULL,
          CHECK((match_type='GLOBAL_RANKED' AND league_id IS NULL AND global_ranking_eligible=1)
             OR (match_type='SPONSORED_LEAGUE' AND league_id IS NOT NULL AND global_ranking_eligible=0)));
        CREATE TABLE IF NOT EXISTS gb_legacy_fixture_origins(
          fixture TEXT PRIMARY KEY, match_type TEXT NOT NULL DEFAULT 'LEGACY_COMPETITION',
          league_id TEXT NOT NULL, historically_rated INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS gb_player_reservations(
          uid TEXT PRIMARY KEY, match TEXT NOT NULL REFERENCES gb_matches(id), created INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS gb_match_times(match TEXT PRIMARY KEY,accepted_at INTEGER,resolved_at INTEGER);
        CREATE TABLE IF NOT EXISTS gb_match_cooldowns(
          game TEXT,low TEXT,high TEXT,until INTEGER NOT NULL,PRIMARY KEY(game,low,high));
        CREATE TRIGGER IF NOT EXISTS gb_origin_no_update BEFORE UPDATE ON gb_match_origins
          BEGIN SELECT RAISE(ABORT,'Match origin is immutable'); END;
        CREATE TRIGGER IF NOT EXISTS gb_origin_no_delete BEFORE DELETE ON gb_match_origins
          BEGIN SELECT RAISE(ABORT,'Match origin cannot be erased'); END;
        CREATE TRIGGER IF NOT EXISTS gb_participants_immutable
          BEFORE UPDATE OF id,game,a,b,gid_a,gid_b ON gb_matches
          BEGIN SELECT RAISE(ABORT,'Match participants and game snapshots are immutable'); END;
        CREATE TRIGGER IF NOT EXISTS gb_origin_on_create AFTER INSERT ON gb_matches BEGIN
          INSERT OR IGNORE INTO gb_match_origins VALUES(NEW.id,'GLOBAL_RANKED',NULL,1);
          INSERT INTO gb_match_times(match) VALUES(NEW.id);
          INSERT INTO gb_player_reservations SELECT NEW.a,NEW.id,NEW.created
            WHERE NEW.state NOT IN ('verified','cancelled');
          INSERT INTO gb_player_reservations SELECT NEW.b,NEW.id,NEW.created
            WHERE NEW.state NOT IN ('verified','cancelled');
          DELETE FROM sl_queue WHERE uid IN (NEW.a,NEW.b);
          DELETE FROM gb_queue WHERE uid IN (NEW.a,NEW.b);
        END;
        CREATE TRIGGER IF NOT EXISTS gb_resolve_reservation AFTER UPDATE OF state ON gb_matches
          WHEN NEW.state IN ('verified','cancelled') BEGIN
          DELETE FROM gb_player_reservations WHERE match=NEW.id;
          UPDATE gb_match_times SET resolved_at=COALESCE(resolved_at,CAST(strftime('%s','now') AS INTEGER))
            WHERE match=NEW.id;
        END;
        CREATE TRIGGER IF NOT EXISTS gb_accept_time AFTER UPDATE OF state ON gb_matches
          WHEN NEW.state='awaiting_checkin' BEGIN
          UPDATE gb_match_times SET accepted_at=COALESCE(accepted_at,CAST(strftime('%s','now') AS INTEGER))
            WHERE match=NEW.id;
        END;
        """)
        d.execute("BEGIN IMMEDIATE")
        if not d.execute("SELECT 1 FROM gb_competition_migrations WHERE version=1").fetchone():
            # gb_matches historically contains open ranked play; league/cup fixtures use fixtures.
            conflicts = d.execute("""SELECT uid FROM (
                SELECT a uid FROM gb_matches WHERE state NOT IN ('verified','cancelled')
                UNION ALL SELECT b FROM gb_matches WHERE state NOT IN ('verified','cancelled'))
                GROUP BY uid HAVING COUNT(*)>1""").fetchall()
            if conflicts:
                raise ValueError("Resolve overlapping legacy player commitments before migrating")
            d.execute("""INSERT OR IGNORE INTO gb_match_origins
                         SELECT id,'GLOBAL_RANKED',NULL,1 FROM gb_matches""")
            d.execute("""INSERT OR IGNORE INTO gb_legacy_fixture_origins
                SELECT f.id,'LEGACY_COMPETITION',f.league,
                EXISTS(SELECT 1 FROM gb_rating_events e WHERE e.fixture=f.id) FROM fixtures f""")
            d.execute("INSERT OR IGNORE INTO gb_match_times(match) SELECT id FROM gb_matches")
            for m in d.execute("SELECT id,a,b,created FROM gb_matches WHERE state NOT IN ('verified','cancelled')").fetchall():
                for uid in (m["a"], m["b"]):
                    d.execute("INSERT OR IGNORE INTO gb_player_reservations VALUES(?,?,?)", (uid, m["id"], m["created"]))
            d.execute("INSERT INTO gb_competition_migrations VALUES(1,?)", (int(time.time()),))


def origin(d, mid):
    row = d.execute("SELECT * FROM gb_match_origins WHERE match=?", (mid,)).fetchone()
    if not row:
        raise ValueError("Match has no authoritative competition origin")
    return dict(row)


def reserve_origin(d, mid, league):
    # Insert before gb_matches within the same transaction; the automatic global
    # trigger must not classify this match as ranked.
    d.execute("INSERT INTO gb_match_origins VALUES(?,'SPONSORED_LEAGUE',?,0)", (mid, league))


def is_global(d, mid):
    return bool(origin(d, mid)["global_ranking_eligible"])


def decorate(d, match):
    times = d.execute("SELECT accepted_at,resolved_at FROM gb_match_times WHERE match=?", (match["id"],)).fetchone()
    return dict(match, **origin(d, match["id"]), match_id=match["id"],
                accepted_at=times["accepted_at"] if times else None,
                resolved_at=times["resolved_at"] if times else None)


def busy(d, uid):
    return bool(d.execute("SELECT 1 FROM gb_player_reservations WHERE uid=?", (uid,)).fetchone())
