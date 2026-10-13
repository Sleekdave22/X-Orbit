"""Clutch Naija pilot: account-bound competitions and auditable match results."""
import base64,hashlib,json,re,time,uuid,subprocess
from pathlib import Path
GAMES={'efootball':'eFootball','fc_mobile':'EA FC Mobile','codm':'CODM 1v1'}
def init(server):
 with server.db() as d:d.executescript('''
 CREATE TABLE IF NOT EXISTS game_profiles(uid TEXT PRIMARY KEY,tag TEXT NOT NULL,game_id TEXT NOT NULL,handle TEXT NOT NULL DEFAULT '',feature INTEGER NOT NULL DEFAULT 0,adult INTEGER NOT NULL);
 CREATE TABLE IF NOT EXISTS leagues(id TEXT PRIMARY KEY,name TEXT NOT NULL,game TEXT NOT NULL,owner TEXT NOT NULL,state TEXT NOT NULL DEFAULT 'enrolling',created INTEGER NOT NULL,sponsor TEXT NOT NULL DEFAULT '',sponsor_url TEXT NOT NULL DEFAULT '',reward TEXT NOT NULL DEFAULT 'Recognition and winner feature; no cash prize',champion TEXT);
 CREATE TABLE IF NOT EXISTS league_members(league TEXT,uid TEXT,game_id TEXT NOT NULL DEFAULT '',PRIMARY KEY(league,uid));
 CREATE TABLE IF NOT EXISTS game_moderators(league TEXT,uid TEXT,PRIMARY KEY(league,uid));
 CREATE TABLE IF NOT EXISTS fixtures(id TEXT PRIMARY KEY,league TEXT,round INTEGER,a TEXT,b TEXT,opens INTEGER,due INTEGER,state TEXT DEFAULT 'scheduled',score_a INTEGER,score_b INTEGER,stage TEXT DEFAULT 'league');
 CREATE TABLE IF NOT EXISTS game_reports(fixture TEXT,uid TEXT,score_a INTEGER,score_b INTEGER,image BLOB,mime TEXT,digest TEXT UNIQUE,ocr TEXT,PRIMARY KEY(fixture,uid));
 CREATE TABLE IF NOT EXISTS game_audit(id INTEGER PRIMARY KEY,fixture TEXT,actor TEXT,action TEXT,details TEXT,time INTEGER);
 ''')
 with server.db() as d:
  if 'game_id' not in {r[1] for r in d.execute('PRAGMA table_info(league_members)')}:d.execute("ALTER TABLE league_members ADD COLUMN game_id TEXT NOT NULL DEFAULT ''")
def row(d,sql,args=()):
 r=d.execute(sql,args).fetchone();return dict(r) if r else None
def mod(d,l,uid):return uid==l['owner'] or bool(d.execute('SELECT 1 FROM game_moderators WHERE league=? AND uid=?',(l['id'],uid)).fetchone())
def audit(d,f,uid,action,details=''):d.execute('INSERT INTO game_audit(fixture,actor,action,details,time) VALUES(?,?,?,?,?)',(f,uid,action,details,int(time.time())))
def standings(d,l):
 people=[dict(r)|{'played':0,'wins':0,'draws':0,'losses':0,'gf':0,'ga':0,'points':0} for r in d.execute('SELECT p.uid,p.tag,p.handle,p.feature FROM game_profiles p JOIN league_members m ON m.uid=p.uid WHERE m.league=?',(l,))];lookup={r['uid']:r for r in people}
 for r in people:
  if not r['feature']:r['handle']=''
 for f in d.execute("SELECT * FROM fixtures WHERE league=? AND state='confirmed' AND stage='league'",(l,)):
  for uid,own,other in ((f['a'],f['score_a'],f['score_b']),(f['b'],f['score_b'],f['score_a'])):
   r=lookup[uid];r['played']+=1;r['gf']+=own;r['ga']+=other;r['wins']+=own>other;r['draws']+=own==other;r['losses']+=own<other;r['points']+=3 if own>other else 1 if own==other else 0
 return sorted(people,key=lambda r:(-r['points'],-(r['gf']-r['ga']),-r['gf'],-r['wins'],r['tag'].lower(),r['uid']))
def summary(server,uid,lid=None):
 with server.db() as d:
  profile=row(d,'SELECT * FROM game_profiles WHERE uid=?',(uid,));leagues=[dict(r) for r in d.execute('SELECT * FROM leagues ORDER BY created DESC')];result={'profile':profile,'leagues':leagues,'games':GAMES,'champions':[]}
  for l in leagues:
   if l['champion']:
    p=row(d,'SELECT uid,tag,handle,feature FROM game_profiles WHERE uid=?',(l['champion'],))
    if p and p['feature']:result['champions'].append(p|{'league':l['name'],'league_id':l['id'],'game':GAMES[l['game']]})
  if lid:
   l=row(d,'SELECT * FROM leagues WHERE id=?',(lid,))
   if not l:raise ValueError('League not found')
   fixtures=[dict(r) for r in d.execute('SELECT f.*,pa.tag name_a,pb.tag name_b FROM fixtures f JOIN game_profiles pa ON pa.uid=f.a JOIN game_profiles pb ON pb.uid=f.b WHERE league=? ORDER BY opens,round',(lid,))]
   for f in fixtures:
    f['can_report']=uid in (f['a'],f['b']) and f['state'] not in ('confirmed','void')
    reports=[dict(r) for r in d.execute('SELECT uid,score_a,score_b,mime,ocr FROM game_reports WHERE fixture=?',(f['id'],))] if uid in (f['a'],f['b']) or mod(d,l,uid) else []
    f['reports']=reports;f['game_ids']={r['uid']:r['game_id'] for r in d.execute('SELECT uid,game_id FROM league_members WHERE league=? AND uid IN (?,?)',(lid,f['a'],f['b']))} if uid in (f['a'],f['b']) or mod(d,l,uid) else {};f['can_review']=mod(d,l,uid) and uid not in (f['a'],f['b']);f['audit']=[dict(r) for r in d.execute('SELECT action,details,time FROM game_audit WHERE fixture=? ORDER BY id',(f['id'],))] if f['can_review'] else []
   result.update(league=l,table=standings(d,lid),fixtures=fixtures,organiser=mod(d,l,uid),owner=uid==l['owner'],joined=bool(d.execute('SELECT 1 FROM league_members WHERE league=? AND uid=?',(lid,uid)).fetchone()))
  return result

def scan(server,image,mime):
 try:
  from gaming_ocr import read
  return read(image)
 except Exception:return {'available':False,'text':'','scores':[],'note':'Automatic reading unavailable; enter the visible score manually.'}

def image(body):
 raw=base64.b64decode(body.get('image',''),validate=True)
 if not 0<len(raw)<=5*1024*1024:raise ValueError('Screenshot must be under 5 MB')
 mime='image/png' if raw.startswith(b'\x89PNG\r\n\x1a\n') else 'image/jpeg' if raw.startswith(b'\xff\xd8\xff') else None
 if not mime:raise ValueError('Use a PNG or JPEG screenshot')
 return raw,mime

def post(server,uid,action,b):
 if action=='scan':
  raw,mime=image(b);return scan(server,raw,mime)
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  if action=='profile':
   if b.get('adult') is not True:raise ValueError('This pilot is for adults aged 18 and over')
   tag=str(b.get('tag','')).strip();gid=str(b.get('game_id','')).strip();handle=str(b.get('handle','')).strip()
   if not 2<=len(tag)<=30 or not 2<=len(gid)<=60 or len(handle)>80:raise ValueError('Enter a gaming nickname and game account ID')
   d.execute('INSERT INTO game_profiles VALUES(?,?,?,?,?,1) ON CONFLICT(uid) DO UPDATE SET tag=excluded.tag,game_id=excluded.game_id,handle=excluded.handle,feature=excluded.feature,adult=1',(uid,tag,gid,handle,int(b.get('feature') is True)));return {'ok':True}
  if action=='create':
   if not row(d,'SELECT * FROM game_profiles WHERE uid=?',(uid,)):raise ValueError('Set up your gaming profile first')
   name=str(b.get('name','')).strip();game=b.get('game')
   if not 3<=len(name)<=60 or game not in GAMES:raise ValueError('Enter a league name and supported game')
   if d.execute("SELECT COUNT(*) FROM leagues WHERE owner=? AND state!='finished'",(uid,)).fetchone()[0]>=3:raise ValueError('Finish an existing league before creating another')
   lid=uuid.uuid4().hex;d.execute('INSERT INTO leagues(id,name,game,owner,created) VALUES(?,?,?,?,?)',(lid,name,game,uid,int(time.time())));return {'id':lid}
  l=row(d,'SELECT * FROM leagues WHERE id=?',(b.get('league'),))
  if not l:raise ValueError('League not found')
  if action=='join':
   if l['state']!='enrolling':raise ValueError('Enrolment is closed')
   if not row(d,'SELECT * FROM game_profiles WHERE uid=?',(uid,)):raise ValueError('Set up your gaming profile first')
   if d.execute('SELECT COUNT(*) FROM league_members WHERE league=?',(l['id'],)).fetchone()[0]>=8:raise ValueError('This division is full')
   d.execute('INSERT OR IGNORE INTO league_members(league,uid,game_id) VALUES(?,?,?)',(l['id'],uid,row(d,'SELECT game_id FROM game_profiles WHERE uid=?',(uid,))['game_id']));return {'ok':True}
  if action in ('start','sponsor','moderator','finals'):
   if uid!=l['owner']:raise PermissionError('Only the league organiser can do this')
   if action=='moderator':
    target=row(d,'SELECT id FROM users WHERE id=? OR nickname=? COLLATE NOCASE',(b.get('identity'),str(b.get('identity','')).lstrip('@')))
    if not target:raise ValueError('Moderator account not found')
    d.execute('INSERT OR IGNORE INTO game_moderators VALUES(?,?)',(l['id'],target['id']));return {'ok':True}
   if action=='sponsor':
    sponsor=str(b.get('sponsor','')).strip();url=str(b.get('url','')).strip()
    if len(sponsor)>60 or len(url)>300 or url and not re.fullmatch(r'https://[^\s]+',url):raise ValueError('Sponsor link must start with https://')
    reward=str(b.get('reward',l['reward'])).strip()
    if not 1<=len(reward)<=250:raise ValueError('Describe the confirmed reward in 250 characters or fewer')
    if reward!=l['reward'] and (l['state']!='enrolling' or b.get('funded') is not True):raise ValueError('Only secured rewards may be announced before the division starts')
    d.execute('UPDATE leagues SET sponsor=?,sponsor_url=?,reward=? WHERE id=?',(sponsor,url,reward,l['id']));return {'ok':True}
   if action=='start':
    if l['state']!='enrolling':raise ValueError('League has already started')
    ids=[r[0] for r in d.execute('SELECT uid FROM league_members WHERE league=? ORDER BY uid',(l['id'],))]
    if len(ids)!=8:raise ValueError('Eight players are required')
    now=int(time.time())
    for n in range(7):
     for i in range(4):d.execute('INSERT INTO fixtures(id,league,round,a,b,opens,due) VALUES(?,?,?,?,?,?,?)',(uuid.uuid4().hex,l['id'],n+1,ids[i],ids[7-i],now+n*4*86400,now+(n+1)*4*86400))
     ids=[ids[0],ids[-1],*ids[1:-1]]
    d.execute("UPDATE leagues SET state='active' WHERE id=?",(l['id'],));return {'ok':True}
   if action=='finals':
    if l['state']!='active' or d.execute("SELECT COUNT(*) FROM fixtures WHERE league=? AND stage='league' AND state!='confirmed'",(l['id'],)).fetchone()[0]:raise ValueError('Confirm every league fixture before seeding finals')
    top=standings(d,l['id'])[:4];now=int(time.time())
    for a,z in ((0,3),(1,2)):d.execute("INSERT INTO fixtures(id,league,round,a,b,opens,due,stage) VALUES(?,?,?,?,?,?,?,'semi')",(uuid.uuid4().hex,l['id'],8,top[a]['uid'],top[z]['uid'],now,now+3*86400))
    d.execute("UPDATE leagues SET state='finals' WHERE id=?",(l['id'],));return {'ok':True}
  f=row(d,'SELECT * FROM fixtures WHERE id=? AND league=?',(b.get('fixture'),l['id']))
  if not f:raise ValueError('Fixture not found')
  if action in ('report','confirm','dispute'):
   if uid not in (f['a'],f['b']):raise PermissionError('Only the scheduled players may submit this result')
   if f['state'] in ('confirmed','void'):raise ValueError('Result is already closed')
   if time.time()<f['opens']:raise ValueError('This match window has not opened')
   if action=='dispute':
    reason=str(b.get('reason','')).strip()
    if len(reason)<5 or len(reason)>500:raise ValueError('Describe the disagreement')
    d.execute("UPDATE fixtures SET state='disputed' WHERE id=?",(f['id'],));audit(d,f['id'],uid,'disputed',reason);return {'ok':True}
   if action=='confirm':
    r=row(d,'SELECT * FROM game_reports WHERE fixture=? AND uid!=?',(f['id'],uid))
    if not r:raise ValueError('The opponent must submit first')
    if f['state']=='disputed':raise ValueError('A moderator must settle the dispute')
    d.execute('INSERT INTO game_reports(fixture,uid,score_a,score_b) VALUES(?,?,?,?) ON CONFLICT(fixture,uid) DO UPDATE SET score_a=excluded.score_a,score_b=excluded.score_b',(f['id'],uid,r['score_a'],r['score_b']));audit(d,f['id'],uid,'confirmed_by_opponent')
   else:
    a=b.get('score_a');z=b.get('score_b')
    if type(a)!=int or type(z)!=int or not 0<=a<=99 or not 0<=z<=99:raise ValueError('Scores must be whole numbers from 0 to 99')
    if f['stage']!='league' and a==z:raise ValueError('Knockout matches need a winner after the agreed tie-break')
    raw,mime=image(b);digest=hashlib.sha256(raw).hexdigest()
    previous=row(d,'SELECT fixture,uid FROM game_reports WHERE digest=?',(digest,))
    if previous and (previous['fixture']!=f['id'] or previous['uid']!=uid):raise ValueError('This screenshot was already submitted. Use your original evidence.')
    d.execute('INSERT INTO game_reports VALUES(?,?,?,?,?,?,?,?) ON CONFLICT(fixture,uid) DO UPDATE SET score_a=excluded.score_a,score_b=excluded.score_b,image=excluded.image,mime=excluded.mime,digest=excluded.digest,ocr=excluded.ocr',(f['id'],uid,a,z,raw,mime,digest,str(b.get('ocr',''))[:6000]));audit(d,f['id'],uid,'submitted')
   reports=list(d.execute('SELECT score_a,score_b FROM game_reports WHERE fixture=?',(f['id'],)))
   if len(reports)==2 and tuple(reports[0])==tuple(reports[1]) and f['state']!='disputed':
    d.execute("UPDATE fixtures SET state='confirmed',score_a=?,score_b=? WHERE id=?",(*reports[0],f['id']));audit(d,f['id'],uid,'result_counted');advance(d,l)
   elif len(reports)==2:d.execute("UPDATE fixtures SET state='disputed' WHERE id=?",(f['id'],))
   else:d.execute("UPDATE fixtures SET state='pending' WHERE id=?",(f['id'],))
   return {'ok':True}
  if action=='review':
   if not mod(d,l,uid) or uid in (f['a'],f['b']):raise PermissionError('An independent league moderator must review this match')
   if f['state'] not in ('pending','disputed'):raise ValueError('This result is not awaiting review')
   reason=str(b.get('reason','')).strip();a=b.get('score_a');z=b.get('score_b')
   if len(reason)<5 or len(reason)>500 or type(a)!=int or type(z)!=int or not 0<=a<=99 or not 0<=z<=99 or f['stage']!='league' and a==z:raise ValueError('Enter the reviewed score and decision reason')
   if not d.execute('SELECT 1 FROM game_reports WHERE fixture=? AND image IS NOT NULL',(f['id'],)).fetchone():raise ValueError('Screenshot evidence is required')
   d.execute("UPDATE fixtures SET state='confirmed',score_a=?,score_b=? WHERE id=?",(a,z,f['id']));audit(d,f['id'],uid,'moderator_approved',reason);advance(d,l);return {'ok':True}
  raise ValueError('Unknown gaming action')
def advance(d,l):
 semis=[dict(r) for r in d.execute("SELECT * FROM fixtures WHERE league=? AND stage='semi'",(l['id'],))]
 if len(semis)==2 and all(f['state']=='confirmed' for f in semis) and not d.execute("SELECT 1 FROM fixtures WHERE league=? AND stage='final'",(l['id'],)).fetchone():
  winners=[f['a'] if f['score_a']>f['score_b'] else f['b'] for f in semis];now=int(time.time());d.execute("INSERT INTO fixtures(id,league,round,a,b,opens,due,stage) VALUES(?,?,?,?,?,?,?,'final')",(uuid.uuid4().hex,l['id'],9,*winners,now,now+3*86400))
 final=row(d,"SELECT * FROM fixtures WHERE league=? AND stage='final' AND state='confirmed'",(l['id'],))
 if final:d.execute("UPDATE leagues SET state='finished',champion=? WHERE id=?",(final['a'] if final['score_a']>final['score_b'] else final['b'],l['id']))
def evidence(server,uid,fid,player):
 with server.db() as d:
  f=row(d,'SELECT * FROM fixtures WHERE id=?',(fid,));l=row(d,'SELECT * FROM leagues WHERE id=?',(f['league'],)) if f else None
  if not f or uid not in (f['a'],f['b']) and not mod(d,l,uid):raise PermissionError('This match evidence is private')
  r=row(d,'SELECT image,mime FROM game_reports WHERE fixture=? AND uid=?',(fid,player))
  if not r or not r['image']:raise ValueError('Screenshot unavailable')
  return r['image'],r['mime']
