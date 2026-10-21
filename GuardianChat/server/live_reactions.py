"""Bounded transient live reactions. No reaction animation is written to SQLite."""
import time,threading,itertools
_lock=threading.Lock();_rooms={};_sequence=itertools.count(1)
ALLOWED=('❤️','👏','🔥','🎉','🏆','😂')
def emit(room,uid,emoji):
 if emoji not in ALLOWED:raise ValueError('Choose a supported live reaction')
 with _lock:
  now=time.monotonic();events=[e for e in _rooms.get(room,[]) if e['at']>now-8]
  if sum(e['uid']==uid for e in events)>=6:raise ValueError('Please slow down')
  events.append({'id':next(_sequence),'uid':uid,'emoji':emoji,'at':now});_rooms[room]=events[-100:]
def read(room):
 with _lock:return [{k:e[k] for k in ('id','emoji')} for e in _rooms.get(room,[]) if e['at']>time.monotonic()-8]
def discard(room):
 with _lock:_rooms.pop(room,None)
