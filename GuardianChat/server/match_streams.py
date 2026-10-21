"""Authenticated match-linked directory. Private invitation rooms stay private.

Directory membership requires a connected relay publisher sending real video;
creating a room or merely marking a player online never makes a stream live.
"""
import time
import uuid

OPEN_STATES = {'accepted', 'confirmed', 'awaiting_checkin', 'in_progress', 'awaiting_results'}
FIXTURE_STATES = {'scheduled', 'accepted', 'confirmed_in', 'in_progress', 'pending', 'awaiting_results'}


def row(d, sql, args=()):
    found = d.execute(sql, args).fetchone()
    return dict(found) if found else None


def init(server):
    with server.db() as d:
        d.executescript('''
        CREATE TABLE IF NOT EXISTS game_stream_links(
            room TEXT PRIMARY KEY, kind TEXT NOT NULL CHECK(kind IN ('open','fixture')),
            match_id TEXT NOT NULL, host TEXT NOT NULL,
            UNIQUE(kind,match_id,host));
        CREATE TABLE IF NOT EXISTS game_stream_transport(
            room TEXT PRIMARY KEY, media TEXT NOT NULL CHECK(media='relay'));
        ''')


def relay_available(server):
    relay = getattr(server, 'stream_relay', None)
    return relay is not None and getattr(relay, 'enabled', True) is not False


def ready(server, rid):
    return bool(relay_available(server) and server.stream_relay.ready(rid))


def account(d, uid):
    if not uid or not d.execute('SELECT 1 FROM users WHERE id=?', (uid,)).fetchone():
        raise PermissionError('Sign in to view this livestream')


def match(d, kind, mid):
    now = int(time.time())
    if kind == 'open':
        m = row(d, 'SELECT id,game,a,b,state,deadline FROM gb_matches WHERE id=?', (mid,))
        if not m or m['state'] not in OPEN_STATES or m['deadline'] < now:
            raise PermissionError('This match is not available for a live broadcast')
        m['context'] = 'Open match'
    elif kind == 'fixture':
        m = row(d, '''SELECT f.id,l.game,f.a,f.b,f.state,f.opens,f.due,l.name context,
                   l.state competition_state FROM fixtures f JOIN leagues l ON l.id=f.league WHERE f.id=?''', (mid,))
        if (not m or m['state'] not in FIXTURE_STATES or m['competition_state'] not in ('active', 'finals')
                or not m['opens'] <= now <= m['due']):
            raise PermissionError('This fixture is not in its active broadcast window')
    else:
        raise ValueError('Choose an open match or competition fixture')
    if not m['a'] or not m['b']:
        raise PermissionError('This match needs both assigned players')
    m['kind'] = kind
    return m


def linked(d, rid):
    return row(d, 'SELECT * FROM game_stream_links WHERE room=?', (rid,))


def access(d, uid, rid, publish=False):
    """DB-scoped authorization shared with existing comments and reactions."""
    account(d, uid)
    room = row(d, 'SELECT * FROM game_stream_rooms WHERE id=?', (rid,))
    if not room or room['created'] < time.time() - 7200:
        raise PermissionError('This live room is unavailable')
    import social
    social.ensure(d, uid, room['a'])
    link = linked(d, rid)
    if link:
        m = match(d, link['kind'], link['match_id'])
        for player in (m['a'], m['b']):
            social.ensure(d, uid, player)
        if room['a'] != link['host'] or room['a'] not in (m['a'], m['b']):
            raise PermissionError('The broadcaster is no longer assigned to this match')
        if publish:
            if uid != room['a']:
                raise PermissionError('Only this room broadcaster may publish')
            profile = row(d, 'SELECT adult FROM game_profiles WHERE uid=?', (uid,))
            if not profile or not profile['adult']:
                raise PermissionError('Set up an adult gaming profile before broadcasting')
            if d.execute('SELECT 1 FROM gb_sanctions WHERE uid=? AND game=? AND until>?',
                         (uid, m['game'], int(time.time()))).fetchone():
                raise PermissionError('Broadcasting is unavailable for this game account')
        elif uid != room['a']:
            member = d.execute('SELECT 1 FROM game_stream_members WHERE room=? AND uid=?', (rid, uid)).fetchone()
            response = row(d, 'SELECT state FROM game_stream_responses WHERE room=? AND uid=?', (rid, uid))
            if not member or not response or response['state'] != 'accepted':
                raise PermissionError('Join this livestream before viewing')
    else:
        if uid != room['a']:
            invited = uid == room['b'] or d.execute('SELECT 1 FROM game_stream_members WHERE room=? AND uid=?', (rid, uid)).fetchone()
            response = row(d, 'SELECT state FROM game_stream_responses WHERE room=? AND uid=?', (rid, uid))
            if not invited or not response or response['state'] != 'accepted':
                raise PermissionError('Accept the live-stream invitation first')
        if publish and uid != room['a']:
            raise PermissionError('Only this room broadcaster may publish')
    return room


def person(d, viewer, pid):
    p = row(d, '''SELECT u.id,u.name,u.nickname,u.avatar,u.avatar_mime,
                 COALESCE(g.feature,0) feature FROM users u LEFT JOIN game_profiles g ON g.uid=u.id WHERE u.id=?''', (pid,))
    if not p:
        return {'id': pid, 'name': 'Player', 'nickname': '', 'avatar': '', 'avatar_mime': ''}
    # Match publicity does not override the existing gaming-photo consent.
    consent = p.pop('feature')
    if viewer != pid and not consent:
        p['avatar'] = ''; p['avatar_mime'] = ''
    return p


def describe(d, server, uid, room):
    import stream_lifecycle as life
    rid = room['id']; link = linked(d, rid)
    response = row(d, 'SELECT state FROM game_stream_responses WHERE room=? AND uid=?', (rid, uid))
    transport = d.execute('SELECT 1 FROM game_stream_transport WHERE room=?', (rid,)).fetchone()
    result = dict(room, media='relay' if link or transport else 'mesh', public=bool(link),
                  live=life.state(d, rid), can_broadcast=uid == room['a'],
                  invitation='accepted' if uid == room['a'] else response['state'] if response else 'invited')
    result['live'].pop('sid', None)
    if link:
        m = match(d, link['kind'], link['match_id'])
        result['match'] = {k: m[k] for k in ('id', 'kind', 'game', 'state', 'context')}
        result['match_kind'] = m['kind']; result['match_id'] = m['id']
        result['players'] = [person(d, uid, p) for p in (m['a'], m['b'])]
        result['share_path'] = '/gaming.html?stream=' + rid
    else:
        result['players'] = [person(d, uid, p) for p in (room['a'], room['b'])]
    result['host'] = person(d, uid, room['a'])
    result['broadcasting'] = bool(result['live']['active'] and ready(server, rid))
    return result


def create(server, uid, body):
    if not relay_available(server):
        raise ValueError('Live match broadcasting is temporarily unavailable; please try again later')
    kind = body.get('kind', 'open'); mid = str(body.get('match') or body.get('match_id') or body.get('fixture') or '')
    with server.db() as d:
        d.execute('BEGIN IMMEDIATE'); account(d, uid)
        m = match(d, kind, mid)
        if uid not in (m['a'], m['b']):
            raise PermissionError('Only these assigned players may broadcast the match')
        __import__('social').ensure(d, m['a'], m['b'])
        existing = row(d, '''SELECT r.* FROM game_stream_rooms r JOIN game_stream_links l ON l.room=r.id
                            WHERE l.kind=? AND l.match_id=? AND l.host=?''', (kind, mid, uid))
        if existing and existing['created'] < time.time() - 7200:
            __import__('stream_lifecycle').finish(d, existing['id'], server); existing = None
        if not existing:
            rid = uuid.uuid4().hex; now = int(time.time()); other = m['b'] if uid == m['a'] else m['a']
            d.execute('INSERT INTO game_stream_rooms VALUES(?,?,?,?)', (rid, uid, other, now))
            d.execute('INSERT INTO game_stream_links VALUES(?,?,?,?)', (rid, kind, mid, uid))
            d.execute("INSERT INTO game_stream_transport VALUES(?,'relay')", (rid,))
            __import__('gamebox_core').event(d, mid, uid, 'match_stream_created', new={'room': rid, 'kind': kind})
            existing = row(d, 'SELECT * FROM game_stream_rooms WHERE id=?', (rid,))
        access(d, uid, existing['id'], publish=True)
        return describe(d, server, uid, existing)


def list_streams(server, uid):
    with server.db() as d:
        account(d, uid); streams = []
        for r in d.execute('''SELECT r.* FROM game_stream_rooms r JOIN game_stream_links l ON l.room=r.id
                              JOIN live_sessions s ON s.room=r.id WHERE r.created>? AND s.heartbeat>?
                              ORDER BY s.started DESC''', (int(time.time()) - 7200, int(time.time()) - 35)).fetchall():
            try:
                room = dict(r); link = linked(d, room['id']); m = match(d, link['kind'], link['match_id'])
                for player in (m['a'], m['b']):
                    __import__('social').ensure(d, uid, player)
                if ready(server, room['id']):
                    streams.append(describe(d, server, uid, room))
            except PermissionError:
                continue
        return {'streams': streams}


def join(server, uid, rid):
    with server.db() as d:
        d.execute('BEGIN IMMEDIATE'); account(d, uid)
        room = row(d, 'SELECT * FROM game_stream_rooms WHERE id=?', (rid,)); link = linked(d, rid)
        if not room or not link:
            raise PermissionError('This public livestream is unavailable')
        m = match(d, link['kind'], link['match_id'])
        if room['created'] < time.time() - 7200 or not ready(server, rid):
            raise PermissionError('This livestream is not broadcasting right now')
        for player in (m['a'], m['b']):
            __import__('social').ensure(d, uid, player)
        __import__('stream_lifecycle').active(d, rid)
        if uid != room['a']:
            d.execute('INSERT OR IGNORE INTO game_stream_members VALUES(?,?)', (rid, uid))
            d.execute("INSERT INTO game_stream_responses VALUES(?,?,'accepted') ON CONFLICT(room,uid) DO UPDATE SET state='accepted'", (rid, uid))
        access(d, uid, rid)
        return describe(d, server, uid, room)


def authorize(server, uid, rid, publish=False):
    with server.db() as d:
        room = access(d, uid, rid, publish=publish)
        if not relay_available(server):
            raise ValueError('Live broadcasting is temporarily unavailable')
        if not publish and not ready(server, rid):
            raise PermissionError('This livestream is not broadcasting right now')
        return describe(d, server, uid, room)
