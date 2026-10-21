"""Ephemeral broadcast sessions; only a broadcaster's aggregate viewer count survives."""
import time,uuid

def init(server):
 with server.db() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS live_sessions(room TEXT PRIMARY KEY,host TEXT NOT NULL,sid TEXT NOT NULL,started INTEGER NOT NULL,heartbeat INTEGER NOT NULL);
  CREATE TABLE IF NOT EXISTS live_viewers(room TEXT NOT NULL,uid TEXT NOT NULL,heartbeat INTEGER NOT NULL,PRIMARY KEY(room,uid));
  CREATE TABLE IF NOT EXISTS live_totals(uid TEXT PRIMARY KEY,viewers INTEGER NOT NULL DEFAULT 0 CHECK(viewers>=0));''')
  # A restarted server has no surviving camera producer.
  for r in d.execute('SELECT room FROM live_sessions').fetchall():finish(d,r['room'])

def active(d,room):
 s=d.execute('SELECT * FROM live_sessions WHERE room=?',(room,)).fetchone()
 if not s:raise PermissionError('This livestream has not started or has ended')
 return dict(s)
def total(d,uid):
 r=d.execute('SELECT viewers FROM live_totals WHERE uid=?',(uid,)).fetchone();return r['viewers'] if r else 0
def finish(d,room,server=None):
 s=d.execute('SELECT * FROM live_sessions WHERE room=?',(room,)).fetchone()
 if s:
  count=d.execute('SELECT COUNT(*) FROM live_viewers WHERE room=?',(room,)).fetchone()[0]
  d.execute('INSERT INTO live_totals(uid,viewers) VALUES(?,?) ON CONFLICT(uid) DO UPDATE SET viewers=viewers+excluded.viewers',(s['host'],count))
 for table in ('game_stream_comments','game_stream_likes','game_stream_signals','game_stream_members','game_stream_responses','live_viewers','live_sessions'):
  d.execute('DELETE FROM '+table+' WHERE room=?',(room,))
 d.execute('DELETE FROM game_stream_rooms WHERE id=?',(room,))
 for table in ('game_stream_links','game_stream_transport'):
  if d.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?",(table,)).fetchone():d.execute('DELETE FROM '+table+' WHERE room=?',(room,))
 __import__("live_reactions").discard(room)
 relay=getattr(server,'stream_relay',None) if server else None
 # end_room schedules shutdown on the media loop and must never re-enter this
 # database transaction synchronously.
 if relay:relay.end_room(room)
 return bool(s)
def begin(d,uid,room):
 r=d.execute('SELECT * FROM game_stream_rooms WHERE id=?',(room,)).fetchone()
 if not r or r['a']!=uid:raise PermissionError('Only this room broadcaster can start the stream')
 s=d.execute('SELECT * FROM live_sessions WHERE room=?',(room,)).fetchone()
 if s:return dict(s)
 for t in ('game_stream_comments','game_stream_likes','game_stream_signals','live_viewers'):d.execute('DELETE FROM '+t+' WHERE room=?',(room,))
 now=int(time.time());sid=uuid.uuid4().hex;d.execute('INSERT INTO live_sessions VALUES(?,?,?,?,?)',(room,uid,sid,now,now));return dict(room=room,host=uid,sid=sid,started=now,heartbeat=now)
def watch(d,uid,room):
 s=active(d,room)
 if uid!=s['host']:d.execute('INSERT INTO live_viewers VALUES(?,?,?) ON CONFLICT(room,uid) DO UPDATE SET heartbeat=excluded.heartbeat',(room,uid,int(time.time())))
 return state(d,room)
def state(d,room):
 s=d.execute('SELECT * FROM live_sessions WHERE room=?',(room,)).fetchone()
 if not s:return {'active':False,'viewers':0,'session_viewers':0}
 return {'active':True,'sid':s['sid'],'viewers':d.execute('SELECT COUNT(*) FROM live_viewers WHERE room=? AND heartbeat>?',(room,int(time.time())-25)).fetchone()[0],'session_viewers':d.execute('SELECT COUNT(*) FROM live_viewers WHERE room=?',(room,)).fetchone()[0]}
def expire(server):
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  ids={r[0] for r in d.execute('SELECT room FROM live_sessions WHERE heartbeat<?',(int(time.time())-35,))}
  ids.update(r[0] for r in d.execute('SELECT id FROM game_stream_rooms WHERE created<?',(int(time.time())-7200,)))
  for link in d.execute('SELECT * FROM game_stream_links').fetchall():
   try:
    m=__import__('match_streams').match(d,link['kind'],link['match_id'])
    __import__('social').ensure(d,m['a'],m['b'])
   except PermissionError:ids.add(link['room'])
  for rid in ids:finish(d,rid,server)
