"""Sponsored competitions reuse gb_matches, independent reports, disputes and notices."""
import json
import secrets
import sqlite3
import time
import uuid

STATES = ("DRAFT", "PUBLISHED", "REGISTRATION_OPEN", "REGISTRATION_CLOSED",
          "ACTIVE", "FINALISING", "COMPLETED", "ARCHIVED", "CANCELLED")
TRANSITIONS = {
    "DRAFT": {"PUBLISHED", "CANCELLED"}, "PUBLISHED": {"REGISTRATION_OPEN", "REGISTRATION_CLOSED", "CANCELLED"},
    "REGISTRATION_OPEN": {"REGISTRATION_CLOSED", "CANCELLED"},
    "REGISTRATION_CLOSED": {"ACTIVE", "CANCELLED"}, "ACTIVE": {"FINALISING"},
    "FINALISING": {"COMPLETED"}, "COMPLETED": {"ARCHIVED"}, "ARCHIVED": set(), "CANCELLED": set(),
}


def schema(d):
    d.executescript("""
    CREATE TABLE IF NOT EXISTS sl_leagues(
      id TEXT PRIMARY KEY,name TEXT NOT NULL,description TEXT NOT NULL,game TEXT NOT NULL,
      platform TEXT NOT NULL,sponsor TEXT NOT NULL,sponsor_url TEXT NOT NULL,prize TEXT NOT NULL,
      registration_opens INTEGER NOT NULL,registration_closes INTEGER NOT NULL,
      starts INTEGER NOT NULL,ends INTEGER NOT NULL,capacity INTEGER NOT NULL,
      state TEXT NOT NULL DEFAULT 'DRAFT',version INTEGER NOT NULL DEFAULT 1,
      rules TEXT NOT NULL,owner TEXT NOT NULL,created INTEGER NOT NULL,final_snapshot TEXT);
    CREATE UNIQUE INDEX IF NOT EXISTS sl_one_active ON sl_leagues(state) WHERE state='ACTIVE';
    CREATE UNIQUE INDEX IF NOT EXISTS sl_one_registration ON sl_leagues(state) WHERE state='REGISTRATION_OPEN';
    CREATE TABLE IF NOT EXISTS sl_registrations(
      league TEXT NOT NULL REFERENCES sl_leagues(id),uid TEXT NOT NULL REFERENCES users(id),
      game_id TEXT NOT NULL,platform TEXT NOT NULL,registered INTEGER NOT NULL,PRIMARY KEY(league,uid));
    CREATE TABLE IF NOT EXISTS sl_queue(
      uid TEXT PRIMARY KEY,league TEXT NOT NULL,created INTEGER NOT NULL,heartbeat INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sl_pair_cooldowns(
      league TEXT,low TEXT,high TEXT,until INTEGER NOT NULL,PRIMARY KEY(league,low,high));
    CREATE TABLE IF NOT EXISTS sl_completed_pairs(
      league TEXT,low TEXT,high TEXT,match TEXT UNIQUE NOT NULL,PRIMARY KEY(league,low,high));
    CREATE TABLE IF NOT EXISTS sl_results(
      match TEXT PRIMARY KEY,league TEXT NOT NULL,a TEXT NOT NULL,b TEXT NOT NULL,
      score_a INTEGER NOT NULL,score_b INTEGER NOT NULL,actor TEXT NOT NULL,created INTEGER NOT NULL);
    CREATE TABLE IF NOT EXISTS sl_appeals(
      match TEXT NOT NULL,uid TEXT NOT NULL,reason TEXT NOT NULL,created INTEGER NOT NULL,
      state TEXT NOT NULL DEFAULT 'pending',reviewer TEXT,decision TEXT,decided INTEGER,
      PRIMARY KEY(match,uid));
    CREATE TABLE IF NOT EXISTS sl_standings(
      league TEXT,uid TEXT,points INTEGER NOT NULL DEFAULT 0,played INTEGER NOT NULL DEFAULT 0,
      wins INTEGER NOT NULL DEFAULT 0,draws INTEGER NOT NULL DEFAULT 0,losses INTEGER NOT NULL DEFAULT 0,
      PRIMARY KEY(league,uid));
    CREATE TABLE IF NOT EXISTS sl_metrics(
      league TEXT,uid TEXT,day INTEGER,PRIMARY KEY(league,uid,day));
    """)


def row(d, sql, args=()):
    value = d.execute(sql, args).fetchone()
    return dict(value) if value else None


def get_league(d, lid):
    league = row(d, "SELECT * FROM sl_leagues WHERE id=?", (lid,))
    if not league:
        raise ValueError("Sponsored league unavailable")
    return league


def event(d, league, actor, action, before=None, after=None, reason=""):
    import gamebox_core
    gamebox_core.event(d, league, actor, "sponsored_" + action, before, after, reason)


def transition(d, league, state, actor, now, reason):
    if state not in TRANSITIONS[league["state"]]:
        raise ValueError("This league state transition is not allowed")
    if len(reason.strip()) < 5:
        raise ValueError("Explain this league transition")
    if state == "REGISTRATION_OPEN" and not league["registration_opens"] <= now < league["registration_closes"]:
        raise ValueError("The registration window is not open")
    if state == "REGISTRATION_CLOSED" and now < league["registration_closes"]:
        raise ValueError("Registration cannot close before the published deadline")
    if state == "ACTIVE" and not league["starts"] <= now < league["ends"]:
        raise ValueError("The scheduled active period has not begun or already ended")
    if state == "FINALISING" and now < league["ends"]:
        raise ValueError("League play ends at the published deadline")
    if state in ("COMPLETED", "CANCELLED") and d.execute(
            """SELECT 1 FROM gb_matches m JOIN gb_match_origins o ON o.match=m.id
               WHERE o.league_id=? AND m.state NOT IN ('verified','cancelled')""", (league["id"],)).fetchone():
        raise ValueError("Resolve outstanding matches before closing this league")
    if state == "COMPLETED" and d.execute("SELECT 1 FROM sl_appeals a JOIN gb_match_origins o ON o.match=a.match WHERE o.league_id=? AND a.state='pending'", (league["id"],)).fetchone():
        raise ValueError("Review pending appeals before completing the league")
    try:
        changed = d.execute("UPDATE sl_leagues SET state=?,version=version+1 WHERE id=? AND version=?",
                            (state, league["id"], league["version"])).rowcount
    except sqlite3.IntegrityError as error:
        raise ValueError("Only one league can be active, and only one can have registration open") from error
    if changed != 1:
        raise ValueError("League changed; reload before continuing")
    if state in ("FINALISING", "CANCELLED"):
        d.execute("DELETE FROM sl_queue WHERE league=?", (league["id"],))
    if state == "COMPLETED":
        snapshot = {"table": table(d, league["id"]), "tie_policy": "Shared positions; prize ties require an approved resolution"}
        d.execute("UPDATE sl_leagues SET final_snapshot=? WHERE id=?", (json.dumps(snapshot), league["id"]))
    event(d, league["id"], actor, "state_changed", league["state"], state, reason)
    import gamebox_core
    for r in d.execute("SELECT uid FROM sl_registrations WHERE league=?", (league["id"],)):
        gamebox_core.notice(d, r["uid"], league["name"] + ": " + state.replace("_", " ").title())


def advance(d, now):
    for league in [dict(r) for r in d.execute(
            "SELECT * FROM sl_leagues WHERE state IN ('PUBLISHED','REGISTRATION_OPEN','REGISTRATION_CLOSED','ACTIVE') ORDER BY starts,created")]:
        state = league["state"]
        target = None
        if state == "PUBLISHED" and now >= league["registration_closes"]:
            target = "REGISTRATION_CLOSED"
        elif state == "PUBLISHED" and now >= league["registration_opens"]:
            target = "REGISTRATION_OPEN"
        elif state == "REGISTRATION_OPEN" and now >= league["registration_closes"]:
            target = "REGISTRATION_CLOSED"
        elif state == "REGISTRATION_CLOSED" and league["starts"] <= now < league["ends"]:
            target = "ACTIVE"
        elif state == "ACTIVE" and now >= league["ends"]:
            target = "FINALISING"
        if target:
            # Another published league can wait; never bypass the singleton index.
            if target in ("ACTIVE", "REGISTRATION_OPEN") and d.execute("SELECT 1 FROM sl_leagues WHERE state=?", (target,)).fetchone():
                continue
            transition(d, league, target, "system", now, "Scheduled lifecycle transition")
    d.execute("DELETE FROM sl_queue WHERE heartbeat<?", (now - 90,))


def table(d, lid):
    output = []
    position = 0
    previous = None
    for index, r in enumerate(d.execute("""SELECT s.*,u.name,u.nickname FROM sl_standings s
             JOIN users u ON u.id=s.uid WHERE league=?
             ORDER BY points DESC,wins DESC,draws DESC,u.id""", (lid,)), 1):
        item = dict(r)
        score = (r["points"], r["wins"], r["draws"])
        if score != previous:
            position = index
        item["position"] = position
        output.append(item)
        previous = score
    return output


def compatible(a, b):
    return a == b or "crossplay" in (a, b)


def identity(d, uid, league):
    import gamebox_core, game_identities
    value = gamebox_core.eligible(d, uid, league["game"])
    meta = game_identities.meta(d, uid, league["game"]) or {}
    if not value or meta.get("platform", "unspecified") == "unspecified":
        raise ValueError("Register this game's ID and choose the platform where you play")
    if not compatible(meta["platform"], league["platform"]):
        raise ValueError("Your gaming platform is incompatible with this league")
    return dict(value, platform=meta["platform"])


def pair(d, league, now):
    import gamebox_core, competition_context, social
    candidates = [dict(r) for r in d.execute("SELECT * FROM sl_queue WHERE league=? AND heartbeat>=? ORDER BY created,uid",
                                            (league["id"], now - 90))]
    for index, a in enumerate(candidates):
        if competition_context.busy(d, a["uid"]):
            continue
        try:
            ai = identity(d, a["uid"], league)
        except ValueError:
            continue
        remaining = candidates[index + 1:]
        secrets.SystemRandom().shuffle(remaining)
        for b in remaining:
            if competition_context.busy(d, b["uid"]) or social.blocked(d, a["uid"], b["uid"]):
                continue
            try:
                bi = identity(d, b["uid"], league)
            except ValueError:
                continue
            low, high = sorted((a["uid"], b["uid"]))
            if not compatible(ai["platform"], bi["platform"]) or ai["region"].casefold() != bi["region"].casefold():
                continue
            if ai["game_id"].casefold() == bi["game_id"].casefold():
                continue
            if d.execute("SELECT 1 FROM sl_completed_pairs WHERE league=? AND low=? AND high=?", (league["id"], low, high)).fetchone():
                continue
            if d.execute("SELECT 1 FROM sl_pair_cooldowns WHERE league=? AND low=? AND high=? AND until>?",
                         (league["id"], low, high, now)).fetchone():
                continue
            mid = uuid.uuid4().hex
            version = gamebox_core.current(d)
            rules = json.loads(league["rules"])
            competition_context.reserve_origin(d, mid, league["id"])
            d.execute("""INSERT INTO gb_matches(id,game,a,b,gid_a,gid_b,state,created,deadline,version,rules)
                         VALUES(?,?,?,?,?,?,'proposed',?,?,?,?)""",
                      (mid, league["game"], a["uid"], b["uid"], ai["game_id"], bi["game_id"], now,
                       now + rules["accept_seconds"], version["id"], league["rules"]))
            d.execute("DELETE FROM sl_queue WHERE uid IN (?,?)", (a["uid"], b["uid"]))
            d.execute("DELETE FROM gb_queue WHERE uid IN (?,?)", (a["uid"], b["uid"]))
            event(d, league["id"], "system", "pair_reserved", after={"match": mid, "a": a["uid"], "b": b["uid"]})
            for uid in (a["uid"], b["uid"]):
                gamebox_core.notice(d, uid, league["name"] + ": league opponent found. Both players must accept.")
            return mid
    return None


def settle(d, match, score_a, score_b, actor):
    import competition_context
    origin = competition_context.origin(d, match["id"])
    if origin["match_type"] != "SPONSORED_LEAGUE" or origin["global_ranking_eligible"]:
        raise ValueError("This result is not a sponsored league match")
    lid = origin["league_id"]
    if d.execute("SELECT 1 FROM sl_results WHERE match=?", (match["id"],)).fetchone():
        return
    for uid in (match["a"], match["b"]):
        if not d.execute("SELECT 1 FROM sl_registrations WHERE league=? AND uid=?", (lid, uid)).fetchone():
            raise ValueError("Both opponents must be registered in this league")
    low, high = sorted((match["a"], match["b"]))
    d.execute("INSERT INTO sl_completed_pairs VALUES(?,?,?,?)", (lid, low, high, match["id"]))
    d.execute("INSERT INTO sl_results VALUES(?,?,?,?,?,?,?,?)",
              (match["id"], lid, match["a"], match["b"], score_a, score_b, actor, int(time.time())))
    for uid, own, other in ((match["a"], score_a, score_b), (match["b"], score_b, score_a)):
        win, draw, loss = int(own > other), int(own == other), int(own < other)
        d.execute("""UPDATE sl_standings SET points=points+?,played=played+1,wins=wins+?,draws=draws+?,losses=losses+?
                     WHERE league=? AND uid=?""", (3 * win + draw, win, draw, loss, lid, uid))
    event(d, lid, actor, "result_awarded", after={"match": match["id"], "score": [score_a, score_b]})


def cancelled(d, match, now, actor=None):
    import competition_context
    origin = competition_context.origin(d, match["id"])
    if origin["match_type"] != "SPONSORED_LEAGUE":
        return False
    lid = origin["league_id"]
    low, high = sorted((match["a"], match["b"]))
    d.execute("INSERT OR REPLACE INTO sl_pair_cooldowns VALUES(?,?,?,?)", (lid, low, high, now + 300))
    league = get_league(d, lid)
    if league["state"] == "ACTIVE" and now < league["ends"]:
        for side in ("a", "b"):
            if match[side] != actor and (actor is not None or match["accepted_" + side] or match["ready_" + side]):
                d.execute("INSERT OR IGNORE INTO sl_queue VALUES(?,?,?,?)", (match[side], lid, now, now))
    return True


def validate(body, now):
    import gaming
    from urllib.parse import urlparse
    fields = {}
    for key, limit in (("name", 100), ("description", 3000), ("sponsor", 100), ("prize", 3000), ("sponsor_url", 500)):
        value = body.get(key, "")
        if not isinstance(value, str) or len(value.strip()) > limit or key == "name" and len(value.strip()) < 3:
            raise ValueError("Check league " + key)
        fields[key] = value.strip()
    fields["game"] = body.get("game")
    fields["platform"] = body.get("platform")
    if fields["game"] not in gaming.GAMES or fields["platform"] not in ("mobile", "console", "pc", "crossplay"):
        raise ValueError("Choose a supported game and gaming platform")
    if fields["sponsor_url"]:
        url = urlparse(fields["sponsor_url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password:
            raise ValueError("Sponsor links must use HTTPS without credentials")
    for key in ("registration_opens", "registration_closes", "starts", "ends", "capacity"):
        if type(body.get(key)) is not int:
            raise ValueError("Use whole-number timestamps and participant capacity")
        fields[key] = body[key]
    if not now - 60 <= fields["registration_opens"] < fields["registration_closes"] <= fields["starts"] < fields["ends"] <= now + 366 * 86400:
        raise ValueError("Keep registration opening/closing and league start/end in chronological order")
    if not 2 <= fields["capacity"] <= 100000:
        raise ValueError("Participant capacity must be between 2 and 100000")
    return fields


def post(server, uid, action, body):
    import gamebox_core, competition_context
    now = int(time.time())
    if action in ("accept", "checkin", "complete", "report", "decline", "evidence", "review"):
        with server.db() as d:
            match = gamebox_core.participant(d, uid, body.get("match")) if action != "review" else row(d, "SELECT * FROM gb_matches WHERE id=?", (body.get("match"),))
            if not match or competition_context.origin(d, match["id"])["match_type"] != "SPONSORED_LEAGUE":
                raise ValueError("Choose the current league match")
        return gamebox_core.post(server, uid, "cancel" if action == "decline" else action, body)
    with server.db() as d:
        d.execute("BEGIN IMMEDIATE")
        advance(d, now)
        if action == "create":
            gamebox_core.authorised(d, uid)
            fields = validate(body, now)
            lid = uuid.uuid4().hex
            rules = json.loads(gamebox_core.current(d)["config"])
            rules["sponsored_review_grace_seconds"] = 172800
            rules = json.dumps(rules)
            values = dict(fields, id=lid, rules=rules, owner=uid, created=now)
            keys = list(values)
            d.execute("INSERT INTO sl_leagues(" + ",".join(keys) + ") VALUES(" + ",".join("?" for _ in keys) + ")", list(values.values()))
            event(d, lid, uid, "created", after=fields)
            return {"league": lid}
        league = get_league(d, body.get("league"))
        lid = league["id"]
        if action == "appeal":
            match = gamebox_core.participant(d, uid, body.get("match"))
            if competition_context.origin(d, match["id"])["league_id"] != lid or match["state"] != "cancelled":
                raise ValueError("Only a voided match in this league can be appealed")
            if league["state"] not in ("ACTIVE", "FINALISING"):
                raise ValueError("In-app appeals close when the league is completed")
            reason = body.get("reason", "")
            if not isinstance(reason, str) or not 10 <= len(reason.strip()) <= 2000:
                raise ValueError("Explain the appeal in 10 to 2000 characters")
            d.execute("INSERT OR IGNORE INTO sl_appeals(match,uid,reason,created) VALUES(?,?,?,?)", (match["id"], uid, reason.strip(), now))
            event(d, lid, uid, "appeal_requested", after={"match":match["id"]}, reason=reason.strip())
            return {"requested": True}
        if action == "appeal_decide":
            gamebox_core.authorised(d, uid)
            match = row(d, "SELECT * FROM gb_matches WHERE id=?", (body.get("match"),))
            if not match or uid in (match["a"], match["b"]) or competition_context.origin(d, match["id"])["league_id"] != lid:
                raise PermissionError("An independent administrator must review this appeal")
            appeal = row(d, "SELECT * FROM sl_appeals WHERE match=? AND uid=?", (match["id"], body.get("player")))
            if not appeal or appeal["state"] != "pending":
                raise ValueError("This appeal is no longer pending")
            decision, reason = body.get("decision"), body.get("reason", "")
            if decision not in ("uphold_void", "reopen_review") or not isinstance(reason,str) or len(reason.strip()) < 10:
                raise ValueError("Choose a decision and record the independent review reason")
            if decision == "reopen_review":
                if league["state"] not in ("ACTIVE", "FINALISING") or match["state"] != "cancelled":
                    raise ValueError("Only an unresolved league may reopen a voided match")
                if any(competition_context.busy(d, player) for player in (match["a"], match["b"])):
                    raise ValueError("Both players must finish their current match before review reopens")
                d.execute("UPDATE gb_matches SET state='review',deadline=? WHERE id=?", (now+json.loads(match["rules"])["evidence_seconds"], match["id"]))
                for player in (match["a"], match["b"]):
                    d.execute("INSERT INTO gb_player_reservations VALUES(?,?,?)", (player,match["id"],now))
                d.execute("DELETE FROM sl_queue WHERE uid IN (?,?)",(match["a"],match["b"]))
                d.execute("DELETE FROM gb_queue WHERE uid IN (?,?)",(match["a"],match["b"]))
            d.execute("UPDATE sl_appeals SET state=?,reviewer=?,decision=?,decided=? WHERE match=? AND uid=?", (decision,uid,reason.strip(),now,match["id"],appeal["uid"]))
            event(d,lid,uid,"appeal_decided",appeal,{"match":match["id"],"decision":decision},reason.strip())
            for player in (match["a"],match["b"]):gamebox_core.notice(d,player,"League appeal reviewed: "+decision.replace("_"," "))
            return {"decided": True}
        if action == "resolve_void":
            gamebox_core.authorised(d, uid)
            match = row(d, "SELECT * FROM gb_matches WHERE id=?", (body.get("match"),))
            if not match or uid in (match["a"], match["b"]) or match["state"] not in ("review", "disputed"):
                raise PermissionError("An independent administrator must review this unresolved match")
            if competition_context.origin(d, match["id"])["league_id"] != lid:
                raise ValueError("The match belongs to a different competition")
            reason = body.get("reason", "")
            if not isinstance(reason, str) or len(reason.strip()) < 10:
                raise ValueError("Record the evidence and reason for voiding")
            d.execute("UPDATE gb_matches SET state='cancelled' WHERE id=?", (match["id"],))
            event(d, lid, uid, "result_voided", match, {"match": match["id"]}, reason.strip())
            return {"voided": True}
        if action in ("edit", "transition"):
            gamebox_core.authorised(d, uid)
            if type(body.get("version")) is not int or body["version"] != league["version"]:
                raise ValueError("League changed; reload before editing")
            if action == "edit":
                if league["state"] != "DRAFT":
                    raise ValueError("Published rules are frozen; create a new draft for a future league")
                fields = validate(body, now)
                d.execute("UPDATE sl_leagues SET " + ",".join(k + "=?" for k in fields) + ",version=version+1 WHERE id=?",
                          list(fields.values()) + [lid])
                event(d, lid, uid, "edited", league, fields)
            else:
                transition(d, league, body.get("state"), uid, now, str(body.get("reason", "")))
            return {"saved": True}
        if league["state"] in ("DRAFT", "CANCELLED"):
            raise ValueError("This league is not available")
        if action == "register":
            if league["state"] != "REGISTRATION_OPEN" or not league["registration_opens"] <= now < league["registration_closes"]:
                raise ValueError("League registration is closed")
            if d.execute("SELECT 1 FROM sl_registrations WHERE league=? AND uid=?", (lid, uid)).fetchone():
                return {"registered": True}
            game = identity(d, uid, league)
            if d.execute("SELECT count(*) FROM sl_registrations WHERE league=?", (lid,)).fetchone()[0] >= league["capacity"]:
                raise ValueError("This league is full")
            d.execute("INSERT INTO sl_registrations VALUES(?,?,?,?,?)", (lid, uid, game["game_id"], game["platform"], now))
            d.execute("INSERT INTO sl_standings(league,uid) VALUES(?,?)", (lid, uid))
            event(d, lid, uid, "registered", after={"game_id": game["game_id"], "platform": game["platform"]})
            return {"registered": True}
        if action == "visit":
            d.execute("INSERT OR IGNORE INTO sl_metrics VALUES(?,?,?)", (lid, uid, now // 86400))
            return {"recorded": True}
        if action == "queue_leave":
            d.execute("DELETE FROM sl_queue WHERE uid=? AND league=?", (uid, lid))
            return {"cancelled": True}
        if action not in ("queue", "heartbeat"):
            raise ValueError("Unknown league action")
        if league["state"] != "ACTIVE" or not league["starts"] <= now < league["ends"]:
            raise ValueError("League matches are available only during the active period")
        if not d.execute("SELECT 1 FROM sl_registrations WHERE league=? AND uid=?", (lid, uid)).fetchone():
            raise ValueError("Register before the league deadline")
        identity(d, uid, league)
        if competition_context.busy(d, uid):
            raise ValueError("Finish your current match before searching")
        total = d.execute("SELECT count(*) FROM sl_registrations WHERE league=? AND uid!=?", (lid, uid)).fetchone()[0]
        played = d.execute("SELECT count(*) FROM sl_completed_pairs WHERE league=? AND (low=? OR high=?)", (lid, uid, uid)).fetchone()[0]
        if played >= total:
            return {"match": None, "state": "exhausted", "message": "No remaining league opponents. You have completed a match against every other participant."}
        if action == "heartbeat" and not d.execute("SELECT 1 FROM sl_queue WHERE uid=? AND league=?", (uid, lid)).fetchone():
            return {"state": "not_searching"}
        d.execute("INSERT INTO sl_queue VALUES(?,?,?,?) ON CONFLICT(uid) DO UPDATE SET heartbeat=excluded.heartbeat",
                  (uid, lid, now, now))
        mid = pair(d, league, now)
        return {"match": mid, "state": "invited" if mid else "searching"}


def get(server, uid, action, query):
    import gamebox_core, gaming, competition_context
    now = int(time.time())
    with server.db() as d:
        d.execute("BEGIN IMMEDIATE")
        advance(d, now)
        admin = gaming.admin(d, uid)
        if action == "audit":
            gamebox_core.authorised(d, uid)
            lid = query.get("league", [""])[0]
            get_league(d, lid)
            return {"events": [dict(r) for r in d.execute("SELECT * FROM gb_events WHERE match=? ORDER BY id DESC LIMIT 200", (lid,))]}
        if action == "appeals":
            gamebox_core.authorised(d, uid)
            return {"appeals": [dict(r) for r in d.execute("SELECT a.*,o.league_id FROM sl_appeals a JOIN gb_match_origins o ON o.match=a.match WHERE a.state='pending' ORDER BY created")]}
        if action == "list":
            rows = d.execute("SELECT * FROM sl_leagues WHERE state!='DRAFT' OR ? ORDER BY created DESC LIMIT 50", (int(admin),))
            return {"leagues": [dict(r, registered=d.execute("SELECT count(*) FROM sl_registrations WHERE league=?", (r["id"],)).fetchone()[0],
                                      joined=bool(d.execute("SELECT 1 FROM sl_registrations WHERE league=? AND uid=?", (r["id"], uid)).fetchone())) for r in rows],
                    "can_admin": admin, "games": gaming.GAMES}
        league = get_league(d, query.get("league", [""])[0])
        if league["state"] == "DRAFT" and not admin:
            raise PermissionError("This league is not published")
        matches = []
        for r in d.execute("""SELECT m.*,a.name name_a,b.name name_b FROM gb_matches m
            JOIN gb_match_origins o ON o.match=m.id JOIN users a ON a.id=m.a JOIN users b ON b.id=m.b
            WHERE o.league_id=? AND (m.a=? OR m.b=?) ORDER BY m.created DESC LIMIT 100""", (league["id"], uid, uid)):
            m = competition_context.decorate(d, dict(r))
            m.pop("rules", None)
            m["my_report"] = row(d, "SELECT a,b FROM gb_reports WHERE match=? AND uid=?", (m["id"], uid))
            matches.append(m)
        return {"league": league, "table": table(d, league["id"]), "matches": matches,
                "joined": bool(d.execute("SELECT 1 FROM sl_registrations WHERE league=? AND uid=?", (league["id"], uid)).fetchone()),
                "queue": row(d, "SELECT * FROM sl_queue WHERE uid=? AND league=?", (uid, league["id"])),
                "can_admin": admin, "metrics": {"registered": d.execute("SELECT count(*) FROM sl_registrations WHERE league=?", (league["id"],)).fetchone()[0],
                    "verified_matches": d.execute("SELECT count(*) FROM sl_results WHERE league=?", (league["id"],)).fetchone()[0]},
                "tie_policy": "Equal points, wins and draws share a position. Prize ties require an approved resolution."}


def tick(server, now=None):
    now = int(time.time()) if now is None else now
    with server.db() as d:
        d.execute("BEGIN IMMEDIATE")
        advance(d, now)
        # A published review deadline resolves unanswered cases without awarding
        # either player's claim. Evidence/events remain available for appeal.
        for match in [dict(r) for r in d.execute("""SELECT m.* FROM gb_matches m
                JOIN gb_match_origins o ON o.match=m.id WHERE o.match_type='SPONSORED_LEAGUE'
                AND m.state IN ('review','disputed') AND m.deadline<?""", (now - 172800,))]:
            d.execute("UPDATE gb_matches SET state='cancelled' WHERE id=?", (match["id"],))
            event(d, __import__("competition_context").origin(d, match["id"])["league_id"], "system",
                  "review_timeout_void", after={"match": match["id"]},
                  reason="Published 48-hour post-review deadline expired; no points awarded. Evidence retained for appeal.")
            for uid in (match["a"], match["b"]):
                __import__("gamebox_core").notice(d, uid, "League review timed out: match void, no points awarded. Contact moderation to appeal.")
        league = row(d, "SELECT * FROM sl_leagues WHERE state='ACTIVE'")
        if league:
            pair(d, league, now)
