"""Account-bound communities and squad discovery, independent of competition results."""
import time,json,uuid
import social

def init(server):
 with server.db() as d:d.executescript('''
 CREATE TABLE IF NOT EXISTS community_spaces(id TEXT PRIMARY KEY,owner TEXT NOT NULL,name TEXT NOT NULL,game TEXT NOT NULL,created INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS community_members(space TEXT,uid TEXT,role TEXT NOT NULL,PRIMARY KEY(space,uid));
 CREATE TABLE IF NOT EXISTS community_posts(id INTEGER PRIMARY KEY,space TEXT NOT NULL,uid TEXT NOT NULL,parent INTEGER,text TEXT NOT NULL,kind TEXT NOT NULL,meta TEXT NOT NULL,created INTEGER NOT NULL,hidden INTEGER NOT NULL DEFAULT 0);
 CREATE TABLE IF NOT EXISTS community_votes(post INTEGER,uid TEXT,choice INTEGER,PRIMARY KEY(post,uid));
 CREATE TABLE IF NOT EXISTS community_likes(post INTEGER,uid TEXT,PRIMARY KEY(post,uid));
 CREATE TABLE IF NOT EXISTS community_moderation(id INTEGER PRIMARY KEY,space TEXT,actor TEXT,post INTEGER,action TEXT,reason TEXT,created INTEGER);
 CREATE TABLE IF NOT EXISTS squad_listings(uid TEXT PRIMARY KEY,game TEXT,region TEXT,language TEXT,platform TEXT,rank TEXT,availability TEXT,created INTEGER);
 ''')

def text(b,key,minimum=0,maximum=100):
 v=b.get(key,'')
 if not isinstance(v,str) or not minimum<=len(v.strip())<=maximum:raise ValueError('Check '+key+' length')
 return v.strip()
def member(d,uid,sid):
 space=d.execute('SELECT * FROM community_spaces WHERE id=?',(sid,)).fetchone()
 if not space:raise ValueError('Community unavailable')
 social.ensure(d,uid,space['owner'])
 role=d.execute('SELECT role FROM community_members WHERE space=? AND uid=?',(sid,uid)).fetchone()
 if not role:raise PermissionError('Join this community first')
 return dict(space),role[0]
def postrow(d,uid,pid):
 p=d.execute('SELECT * FROM community_posts WHERE id=?',(pid,)).fetchone()
 if not p or p['hidden']:raise ValueError('Post unavailable')
 member(d,uid,p['space']);social.ensure(d,uid,p['uid']);return p

def get(server,uid,action,q):
 with server.db() as d:
  if action=='communities':return {'communities':[dict(r) for r in d.execute('SELECT s.*, (SELECT COUNT(*) FROM community_members m WHERE m.space=s.id) members,EXISTS(SELECT 1 FROM community_members m WHERE m.space=s.id AND m.uid=?) joined FROM community_spaces s ORDER BY s.created DESC LIMIT 100',(uid,)) if not social.blocked(d,uid,r['owner'])]}
  if action=='posts':
   sid=q.get('space',[''])[0];space,role=member(d,uid,sid);before=int(q.get('before',['9223372036854775807'])[0]);items=[]
   for p in d.execute('SELECT p.*,u.name,u.nickname FROM community_posts p JOIN users u ON u.id=p.uid WHERE p.space=? AND p.hidden=0 AND p.id<? ORDER BY p.id DESC LIMIT 50',(sid,before)):
    if social.blocked(d,uid,p['uid']):continue
    item=dict(p);item['meta']=json.loads(item['meta']);item['likes']=d.execute('SELECT COUNT(*) FROM community_likes WHERE post=?',(p['id'],)).fetchone()[0];item['votes']=[dict(r) for r in d.execute('SELECT choice,COUNT(*) total FROM community_votes WHERE post=? GROUP BY choice',(p['id'],))];items.append(item)
   return {'space':space,'role':role,'posts':items}
  if action=='moderation':
   sid=q.get('space',[''])[0];space,role=member(d,uid,sid)
   if role!='owner':raise PermissionError('Community owner access required')
   return {'actions':[dict(r) for r in d.execute('SELECT * FROM community_moderation WHERE space=? ORDER BY id DESC LIMIT 100',(sid,))]}
  if action=='squads':
   clauses=['s.created>?'];params=[int(time.time())-86400]
   for key in ('game','region','language','platform','rank','availability'):
    value=q.get(key,[''])[0].strip()
    if value:clauses.append('s.'+key+'=? COLLATE NOCASE');params.append(value)
   rows=d.execute('SELECT s.*,u.name,u.nickname FROM squad_listings s JOIN users u ON u.id=s.uid WHERE '+' AND '.join(clauses)+' ORDER BY s.created DESC LIMIT 100',params)
   return {'listings':[dict(r) for r in rows if not social.blocked(d,uid,r['uid'])]}
  raise ValueError('Unknown community action')

def post(server,uid,action,b):
 now=int(time.time())
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  if action=='squad_remove':d.execute('DELETE FROM squad_listings WHERE uid=?',(uid,));return {'saved':True}
  if action=='squad_save':
   values=[text(b,k,1,80) for k in ('game','region','language','platform','rank','availability')]
   d.execute('INSERT OR REPLACE INTO squad_listings VALUES(?,?,?,?,?,?,?,?)',[uid]+values+[now]);return {'saved':True}
  if action=='create':
   if d.execute('SELECT COUNT(*) FROM community_spaces WHERE owner=?',(uid,)).fetchone()[0]>=5:raise ValueError('You can own up to five pilot communities')
   sid=uuid.uuid4().hex;d.execute('INSERT INTO community_spaces VALUES(?,?,?,?,?)',(sid,uid,text(b,'name',3,80),text(b,'game',0,80),now));d.execute('INSERT INTO community_members VALUES(?,?,?)',(sid,uid,'owner'));return {'id':sid}
  sid=str(b.get('space',''));space=d.execute('SELECT * FROM community_spaces WHERE id=?',(sid,)).fetchone()
  if not space:raise ValueError('Community unavailable')
  social.ensure(d,uid,space['owner'])
  if action=='join':d.execute('INSERT OR IGNORE INTO community_members VALUES(?,?,?)',(sid,uid,'member'));return {'saved':True}
  space,role=member(d,uid,sid)
  if action=='leave':
   if role=='owner':raise ValueError('The owner keeps community responsibility')
   d.execute('DELETE FROM community_members WHERE space=? AND uid=?',(sid,uid));return {'saved':True}
  if action=='publish':
   if d.execute('SELECT COUNT(*) FROM community_posts WHERE uid=? AND created>?',(uid,now-60)).fetchone()[0]>=10:raise ValueError('Please slow down')
   kind=b.get('kind','text');meta={};parent=b.get('parent')
   if kind not in ('text','poll','event','clip'):raise ValueError('Choose a post type')
   if parent is not None:
    original=postrow(d,uid,int(parent))
    if original['space']!=sid:raise ValueError('Reply must stay in its community')
   if kind=='poll':
    options=b.get('options',[])
    if not isinstance(options,list) or not 2<=len(options)<=6 or any(not isinstance(x,str) or not 1<=len(x.strip())<=80 for x in options):raise ValueError('Use 2–6 poll options')
    meta['options']=[x.strip() for x in options]
    if len(set(meta['options']))!=len(options):raise ValueError('Poll options must be different')
   if kind=='event':
    starts=b.get('starts')
    if type(starts) is not int or not now<starts<now+366*86400:raise ValueError('Choose a future event time')
    meta['starts']=starts
   if kind=='clip':
    from urllib.parse import urlparse
    url=text(b,'url',1,1000);parts=urlparse(url)
    if parts.scheme!='https' or not parts.hostname or parts.username or parts.password:raise ValueError('Use an HTTPS clip link')
    meta['url']=url
   cur=d.execute('INSERT INTO community_posts(space,uid,parent,text,kind,meta,created) VALUES(?,?,?,?,?,?,?)',(sid,uid,parent,text(b,'text',1,2000),kind,json.dumps(meta),now))
   if parent is not None and original['uid']!=uid:social.notice(d,original['uid'],uid,'community_reply')
   return {'id':cur.lastrowid}
  if action=='restore':
   if role!='owner':raise PermissionError('Community owner access required')
   pid=int(b.get('post',0));reason=text(b,'reason',5,500)
   if not d.execute('SELECT 1 FROM community_posts WHERE id=? AND space=? AND hidden=1',(pid,sid)).fetchone():raise ValueError('Removed post unavailable')
   d.execute('UPDATE community_posts SET hidden=0 WHERE id=?',(pid,));d.execute('INSERT INTO community_moderation(space,actor,post,action,reason,created) VALUES(?,?,?,?,?,?)',(sid,uid,pid,'restore',reason,now));return {'saved':True}
  pid=int(b.get('post',0));p=postrow(d,uid,pid)
  if p['space']!=sid:raise PermissionError('Post belongs to another community')
  if action=='like':d.execute('INSERT OR IGNORE INTO community_likes VALUES(?,?)',(pid,uid));return {'saved':True}
  if action=='vote':
   choices=json.loads(p['meta']).get('options',[]);choice=b.get('choice')
   if p['kind']!='poll' or type(choice) is not int or not 0<=choice<len(choices):raise ValueError('Choose a valid poll option')
   d.execute('INSERT OR REPLACE INTO community_votes VALUES(?,?,?)',(pid,uid,choice));return {'saved':True}
  if action=='hide':
   if role!='owner' and uid!=p['uid']:raise PermissionError('Only the author or community owner may remove this post')
   reason=text(b,'reason',5,500);d.execute('UPDATE community_posts SET hidden=1 WHERE id=?',(pid,));d.execute('INSERT INTO community_moderation(space,actor,post,action,reason,created) VALUES(?,?,?,?,?,?)',(sid,uid,pid,'hide',reason,now));return {'saved':True}
  raise ValueError('Unknown community action')
