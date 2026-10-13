"""Versioned Gamebox Studio and open-match workflows. Does not edit chat/media security."""
import json,time,uuid,re,math,hashlib,base64
DEFAULT={'accept_seconds':300,'checkin_seconds':600,'result_seconds':3600,'evidence_seconds':86400,'retention_seconds':259200,'reminder_seconds':900,'reschedules':1,'group_size':10,'round_days':3,'max_pair_daily':2,'rating_gap':400,'theme':{'accent':'#921b37','surface':'#252525','paper':'#101010','ink':'#f4f4f4','radius':8,'tab_padding':12,'font_size':14,'font_family':'system-ui'},'layout':['stats','competitions','players','matches'],'announcement':'','show_stats':True}
LIMITS={'accept_seconds':(60,1800),'checkin_seconds':(120,3600),'result_seconds':(1800,7200),'evidence_seconds':(3600,259200),'retention_seconds':(3600,2592000),'reminder_seconds':(60,3600),'reschedules':(0,1),'group_size':(6,16),'round_days':(1,14),'max_pair_daily':(1,3),'rating_gap':(100,800)}
def init(server):
 with server.db() as d:
  d.executescript('''
  CREATE TABLE IF NOT EXISTS gb_comp_retention(fixture TEXT PRIMARY KEY,expires INTEGER);
  CREATE TABLE IF NOT EXISTS gb_walkovers(fixture TEXT PRIMARY KEY,winner TEXT,reason TEXT,actor TEXT,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_schedule(fixture TEXT PRIMARY KEY,proposer TEXT,proposed INTEGER,scheduled INTEGER,confirmed_a INTEGER DEFAULT 0,confirmed_b INTEGER DEFAULT 0,reschedules INTEGER DEFAULT 0,ready_a INTEGER DEFAULT 0,ready_b INTEGER DEFAULT 0,reminded INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS gb_versions(id INTEGER PRIMARY KEY,config TEXT,actor TEXT,reason TEXT,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_draft(id INTEGER PRIMARY KEY CHECK(id=1),base INTEGER,config TEXT);
  CREATE TABLE IF NOT EXISTS gb_game_ids(uid TEXT,game TEXT,game_id TEXT,region TEXT,tz TEXT,availability TEXT,reminders INTEGER DEFAULT 1,PRIMARY KEY(uid,game));
  CREATE TABLE IF NOT EXISTS gb_rating_events(fixture TEXT PRIMARY KEY,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_ratings(uid TEXT,game TEXT,rating REAL DEFAULT 1500,played INTEGER DEFAULT 0,activity INTEGER DEFAULT 0,PRIMARY KEY(uid,game));
  CREATE TABLE IF NOT EXISTS gb_queue(uid TEXT PRIMARY KEY,game TEXT,region TEXT,priority INTEGER DEFAULT 0,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_matches(id TEXT PRIMARY KEY,game TEXT,a TEXT,b TEXT,gid_a TEXT,gid_b TEXT,state TEXT,created INTEGER,deadline INTEGER,accepted_a INTEGER DEFAULT 0,accepted_b INTEGER DEFAULT 0,ready_a INTEGER DEFAULT 0,ready_b INTEGER DEFAULT 0,score_a INTEGER,score_b INTEGER,version INTEGER,rules TEXT,verified INTEGER,rated INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS gb_reports(match TEXT,uid TEXT,a INTEGER,b INTEGER,PRIMARY KEY(match,uid));
  CREATE TABLE IF NOT EXISTS gb_evidence(match TEXT,uid TEXT,image BLOB,mime TEXT,digest TEXT,reading TEXT,expires INTEGER,PRIMARY KEY(match,uid));
  CREATE TABLE IF NOT EXISTS gb_events(id INTEGER PRIMARY KEY,match TEXT,actor TEXT,action TEXT,old TEXT,new TEXT,reason TEXT,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_notice_delivery(id INTEGER PRIMARY KEY,attempts INTEGER DEFAULT 0,next_attempt INTEGER DEFAULT 0,delivered INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS gb_notices(id INTEGER PRIMARY KEY,uid TEXT,text TEXT,created INTEGER,seen INTEGER DEFAULT 0);
  CREATE TABLE IF NOT EXISTS gb_room_messages(id INTEGER PRIMARY KEY,match TEXT,uid TEXT,text TEXT,created INTEGER);
  CREATE TABLE IF NOT EXISTS gb_sanctions(uid TEXT,game TEXT,until INTEGER,reason TEXT,PRIMARY KEY(uid,game));
  ''')
  d.execute('CREATE INDEX IF NOT EXISTS gb_match_a_state ON gb_matches(a,state)');d.execute('CREATE INDEX IF NOT EXISTS gb_match_b_state ON gb_matches(b,state)');d.execute('CREATE INDEX IF NOT EXISTS gb_match_game_created ON gb_matches(game,created)');d.execute('CREATE INDEX IF NOT EXISTS gb_event_match ON gb_events(match,created)');d.execute('CREATE INDEX IF NOT EXISTS gb_room_match ON gb_room_messages(match,id)')
  if not d.execute('SELECT 1 FROM gb_versions').fetchone():d.execute('INSERT INTO gb_versions(config,actor,reason,created) VALUES(?,?,?,?)',(json.dumps(DEFAULT),'system','Initial supported defaults',int(time.time())))
  else:
   existing=row(d,'SELECT * FROM gb_versions ORDER BY id DESC LIMIT 1');old=json.loads(existing['config']);merged=dict(DEFAULT,**old);merged['theme']=dict(DEFAULT['theme'],**old.get('theme',{}))
   if merged!=old:d.execute('INSERT INTO gb_versions(config,actor,reason,created) VALUES(?,?,?,?)',(json.dumps(merged),'migration','Add supported controls while preserving published customisations',int(time.time())))
def row(d,sql,args=()):
 r=d.execute(sql,args).fetchone();return dict(r) if r else None
def current(d):return row(d,'SELECT * FROM gb_versions ORDER BY id DESC LIMIT 1')
def authorised(d,uid):
 import gaming
 if not gaming.admin(d,uid):raise PermissionError('Administration is restricted to the authorised account')
def event(d,mid,uid,action,old=None,new=None,reason=''):
 d.execute('INSERT INTO gb_events(match,actor,action,old,new,reason,created) VALUES(?,?,?,?,?,?,?)',(mid,uid,action,json.dumps(old),json.dumps(new),reason,int(time.time())))
def notice(d,uid,text):d.execute('INSERT INTO gb_notices(uid,text,created) VALUES(?,?,?)',(uid,text,int(time.time())))
def validate(c):
 if type(c)!=dict or set(c)!=set(DEFAULT):raise ValueError('Only supported Studio controls may be changed')
 for k,(lo,hi) in LIMITS.items():
  if type(c[k])!=int or not lo<=c[k]<=hi:raise ValueError(k+' must be between '+str(lo)+' and '+str(hi))
 t=c['theme']
 if type(t)!=dict or set(t)!=set(DEFAULT['theme']):raise ValueError('Unsupported theme controls')
 for k in ['accent','surface','paper','ink']:
  if not re.fullmatch(r'#[0-9a-fA-F]{6}',str(t[k])):raise ValueError('Use six-digit colour values')
 for k,lo,hi in [('radius',0,24),('tab_padding',8,24),('font_size',12,20)]:
  if type(t[k])!=int or not lo<=t[k]<=hi:raise ValueError('Invalid theme sizing')
 if type(c['layout'])!=list or sorted(c['layout'])!=sorted(DEFAULT['layout']):raise ValueError('Reorder existing components only')
 if t['font_family'] not in ('system-ui','sans-serif','serif','monospace'):raise ValueError('Choose a supported built-in font')
 if type(c['show_stats'])!=bool:raise ValueError('Choose whether statistics should be displayed')
 if type(c['announcement'])!=str or len(c['announcement'])>500:raise ValueError('Announcement must be under 500 characters')
 return c
def eligible(d,uid,game):
 import gaming
 if game not in gaming.GAMES:raise ValueError('Choose a supported game')
 if not d.execute('SELECT 1 FROM game_profiles WHERE uid=? AND adult=1',(uid,)).fetchone():raise ValueError('Create your adult gaming profile first')
 if d.execute('SELECT 1 FROM gb_sanctions WHERE uid=? AND game=? AND until>?',(uid,game,int(time.time()))).fetchone():raise ValueError('Gaming access is suspended; contact administration for review')
 return row(d,'SELECT * FROM gb_game_ids WHERE uid=? AND game=?',(uid,game))
def participant(d,uid,mid):
 m=row(d,'SELECT * FROM gb_matches WHERE id=?',(mid,))
 if not m or uid not in (m['a'],m['b']):raise PermissionError('Only the match participants may do this')
 return m

def summary(server,uid):
 with server.db() as d:
  version=current(d);config=json.loads(version['config'])
  matches=[dict(r) for r in d.execute('SELECT m.*,pa.tag name_a,pb.tag name_b FROM gb_matches m JOIN game_profiles pa ON pa.uid=m.a JOIN game_profiles pb ON pb.uid=m.b WHERE a=? OR b=? ORDER BY created DESC LIMIT 30',(uid,uid))]
  for m in matches:
   m.pop('rules',None);m['reports']=[dict(r) for r in d.execute('SELECT * FROM gb_reports WHERE match=?',(m['id'],))]
   if m['state']=='awaiting_results' and not any(r['uid']==uid for r in m['reports']):m['reports']=[{'uid':r['uid'],'submitted':True} for r in m['reports']]
  return {'version':version['id'],'config':config,'ids':[dict(r) for r in d.execute('SELECT * FROM gb_game_ids WHERE uid=?',(uid,))],'ratings':[dict(r) for r in d.execute('SELECT * FROM gb_ratings WHERE uid=?',(uid,))],'queue':row(d,'SELECT * FROM gb_queue WHERE uid=?',(uid,)),'matches':matches,'notices':[dict(r) for r in d.execute('SELECT * FROM gb_notices WHERE uid=? AND seen=0 ORDER BY id DESC LIMIT 30',(uid,))]}
def studio(server,uid):
 with server.db() as d:
  authorised(d,uid)
  return {'published':current(d),'draft':row(d,'SELECT * FROM gb_draft WHERE id=1'),'versions':[dict(r) for r in d.execute('SELECT id,actor,reason,created FROM gb_versions ORDER BY id DESC LIMIT 20')],'limits':LIMITS,'events':[dict(r) for r in d.execute('SELECT * FROM gb_events ORDER BY id DESC LIMIT 100')],'disputes':[dict(r) for r in d.execute("SELECT * FROM gb_matches WHERE state IN ('disputed','review') ORDER BY created")],'sanctions':[dict(r) for r in d.execute('SELECT * FROM gb_sanctions')]}

def pair(d,game,region):
 candidates=[dict(r) for r in d.execute('SELECT q.*,i.game_id,COALESCE(r.rating,1500) rating FROM gb_queue q JOIN gb_game_ids i ON i.uid=q.uid AND i.game=q.game LEFT JOIN gb_ratings r ON r.uid=q.uid AND r.game=q.game WHERE q.game=? AND q.region=? ORDER BY priority DESC,q.created',(game,region))];version=current(d);rules=json.loads(version['config'])
 for i,a in enumerate(candidates):
  for b in candidates[i+1:]:
   if a['game_id'].casefold()==b['game_id'].casefold() or abs(a['rating']-b['rating'])>rules['rating_gap']:continue
   if d.execute("SELECT COUNT(*) FROM gb_matches WHERE game=? AND state='verified' AND created>? AND ((a=? AND b=?) OR (a=? AND b=?))",(game,int(time.time())-86400,a['uid'],b['uid'],b['uid'],a['uid'])).fetchone()[0]>=rules['max_pair_daily']:continue
   mid=uuid.uuid4().hex;now=int(time.time());d.execute('INSERT INTO gb_matches(id,game,a,b,gid_a,gid_b,state,created,deadline,version,rules) VALUES(?,?,?,?,?,?,?, ?,?,?,?)',(mid,game,a['uid'],b['uid'],a['game_id'],b['game_id'],'proposed',now,now+rules['accept_seconds'],version['id'],json.dumps(rules)))
   d.execute('DELETE FROM gb_queue WHERE uid IN (?,?)',(a['uid'],b['uid']));event(d,mid,'system','match_proposed',new={'a':a['uid'],'b':b['uid'],'version':version['id']})
   for u in (a['uid'],b['uid']):notice(d,u,'Opponent found. Both players must accept the proposed match.')
   return mid
 return None

def verify(d,m,a,b,actor,reason='Matching independent typed reports'):
 if m['state']=='verified':raise ValueError('This result is already verified')
 d.execute("UPDATE gb_matches SET state='verified',score_a=?,score_b=?,verified=? WHERE id=?",(a,b,int(time.time()),m['id']))
 old={};new={}
 for uid,other,outcome in [(m['a'],m['b'],1 if a>b else .5 if a==b else 0),(m['b'],m['a'],1 if b>a else .5 if b==a else 0)]:
  for u in (uid,other):d.execute('INSERT OR IGNORE INTO gb_ratings(uid,game) VALUES(?,?)',(u,m['game']))
  old[uid]=row(d,'SELECT * FROM gb_ratings WHERE uid=? AND game=?',(uid,m['game']))
 for uid,other,outcome in [(m['a'],m['b'],1 if a>b else .5 if a==b else 0),(m['b'],m['a'],1 if b>a else .5 if b==a else 0)]:
  expected=1/(1+10**((old[other]['rating']-old[uid]['rating'])/400));rating=round(old[uid]['rating']+24*(outcome-expected),2);new[uid]=rating;d.execute('UPDATE gb_ratings SET rating=?,played=played+1,activity=activity+1 WHERE uid=? AND game=?',(rating,uid,m['game']))
 d.execute('UPDATE gb_matches SET rated=1 WHERE id=?',(m['id'],));event(d,m['id'],actor,'result_verified',old={'reports':[dict(r) for r in d.execute('SELECT * FROM gb_reports WHERE match=?',(m['id'],))],'ratings':old},new={'score':[a,b],'ratings':new},reason=reason)
 rules=json.loads(m['rules']);d.execute('UPDATE gb_evidence SET expires=? WHERE match=?',(int(time.time())+rules['retention_seconds'],m['id']))
 for uid in (m['a'],m['b']):notice(d,uid,'Result verified. Skill rating and participation record updated.')

def post(server,uid,action,b):
 if action=='evidence':
  import gaming
  raw,mime=gaming.image(b);reading=gaming.scan(server,raw,mime);b=dict(b,reading=reading.get('text',''))
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  if action.startswith('studio_'):
   authorised(d,uid);version=current(d)
   if action=='studio_save':
    c=validate(b.get('config'));base=b.get('base')
    if base!=version['id']:raise ValueError('Published settings changed. Reload before saving.')
    d.execute('INSERT OR REPLACE INTO gb_draft VALUES(1,?,?)',(base,json.dumps(c)));event(d,'studio',uid,'draft_saved',new=c);return {'ok':True}
   reason=str(b.get('reason','')).strip()
   if not 5<=len(reason)<=300:raise ValueError('Explain this publish or rollback')
   if action=='studio_publish':
    draft=row(d,'SELECT * FROM gb_draft WHERE id=1')
    if not draft or draft['base']!=version['id']:raise ValueError('Save a current draft first')
    config=draft['config'];validate(json.loads(config))
   elif action=='studio_rollback':
    previous=row(d,'SELECT * FROM gb_versions WHERE id=?',(b.get('version'),))
    if not previous:raise ValueError('Version not found')
    config=previous['config']
   else:raise ValueError('Unknown Studio action')
   d.execute('INSERT INTO gb_versions(config,actor,reason,created) VALUES(?,?,?,?)',(config,uid,reason,int(time.time())));d.execute('DELETE FROM gb_draft');event(d,'studio',uid,action,old=json.loads(version['config']),new=json.loads(config),reason=reason);return {'ok':True}
  if action=='simulate':
   authorised(d,uid);entrants=b.get('entrants');size=b.get('group_size');days=b.get('round_days')
   if any(type(v)!=int for v in (entrants,size,days)) or not 6<=entrants<=100000 or not 6<=size<=16 or not 1<=days<=14:raise ValueError('Simulate 6–100,000 entrants, groups of 6–16, and 1–14 days per round')
   groups=math.ceil(entrants/size);small=entrants//groups;large=small+1;nlarge=entrants%groups;nsmall=groups-nlarge
   if small<6:raise ValueError('Too few players to form groups of at least six; choose a larger group target')
   fixtures=nsmall*small*(small-1)//2+nlarge*large*(large-1)//2;maximum=large if nlarge else small;rounds=maximum if maximum%2 else maximum-1
   return {'entrants':entrants,'groups':groups,'group_distribution':{str(small):nsmall,str(large):nlarge},'fixtures':fixtures,'rounds':rounds,'estimated_days':rounds*days,'note':'Estimate only. Requires mutually available time slots and moderation capacity.'}
  if action=='walkover':
   authorised(d,uid);f=row(d,'SELECT * FROM fixtures WHERE id=?',(b.get('fixture'),));schedule=row(d,'SELECT * FROM gb_schedule WHERE fixture=?',(b.get('fixture'),));league=row(d,'SELECT * FROM leagues WHERE id=?',(f['league'],)) if f else None;rules=json.loads(league['policy_snapshot'] or current(d)['config']) if league else DEFAULT;reason=str(b.get('reason','')).strip()
   if not f or f['stage']!='league' or uid in (f['a'],f['b']) or f['state'] in ('confirmed','void','walkover') or not schedule or not schedule['scheduled'] or time.time()<=schedule['scheduled']+rules['checkin_seconds'] or len(reason)<10:raise PermissionError('An independent administrator may review a documented no-show only after the check-in deadline')
   if schedule['ready_a'] and schedule['ready_b']:raise ValueError('Both players checked in. This is not a no-show')
   winner=f['a'] if schedule['ready_a'] else f['b'] if schedule['ready_b'] else None
   d.execute('INSERT INTO gb_walkovers VALUES(?,?,?,?,?)',(f['id'],winner,reason,uid,int(time.time())))
   d.execute('UPDATE fixtures SET state=? WHERE id=?',('walkover' if winner else 'void',f['id']));event(d,f['id'],uid,'walkover_reviewed',old=schedule,new={'winner':winner,'no_rating_change':True},reason=reason);return {'ok':True}
  if action=='identity':
   game=b.get('game');eligible(d,uid,game);gid=str(b.get('game_id','')).strip();region=str(b.get('region','')).strip();tz=str(b.get('tz','')).strip();slots=b.get('availability',[])
   if not 2<=len(gid)<=60 or not 1<=len(region)<=40 or not 1<=len(tz)<=60 or type(slots)!=list or len(slots)>14:raise ValueError('Enter game ID, region, time zone and availability')
   from zoneinfo import ZoneInfo
   try:ZoneInfo(tz)
   except Exception:raise ValueError('Use a valid time-zone name')
   for slot in slots:
    if type(slot)!=dict or set(slot)!={'start','end'} or type(slot['start'])!=int or type(slot['end'])!=int or not time.time()<slot['start']<slot['end']<=time.time()+60*86400:raise ValueError('Availability must contain future start/end times')
   prior=row(d,'SELECT game_id FROM gb_game_ids WHERE uid=? AND game=?',(uid,game))
   if prior and prior['game_id']!=gid and d.execute("SELECT 1 FROM gb_matches WHERE game=? AND (a=? OR b=?) AND state NOT IN ('verified','cancelled')",(game,uid,uid)).fetchone():raise ValueError('Finish your active match before changing the game ID')
   if d.execute('SELECT 1 FROM gb_game_ids WHERE game=? AND game_id=? COLLATE NOCASE AND uid!=?',(game,gid,uid)).fetchone():raise ValueError('This official game ID is registered to another account')
   existing=row(d,'SELECT * FROM gb_game_ids WHERE uid=? AND game=?',(uid,game));d.execute('INSERT INTO gb_game_ids VALUES(?,?,?,?,?,?,?) ON CONFLICT(uid,game) DO UPDATE SET game_id=excluded.game_id,region=excluded.region,tz=excluded.tz,availability=excluded.availability,reminders=excluded.reminders',(uid,game,gid,region,tz,json.dumps(slots),int(b.get('reminders',True) is True)));event(d,'identity',uid,'game_identity_saved',old=existing,new={'game':game,'game_id':gid});return {'ok':True}
  if action=='queue':
   game=b.get('game');identity=eligible(d,uid,game)
   if not identity:raise ValueError('Register your official ID for this game first')
   if d.execute("SELECT 1 FROM gb_matches WHERE (a=? OR b=?) AND state NOT IN ('verified','cancelled')",(uid,uid)).fetchone():raise ValueError('Finish your active match first')
   d.execute('INSERT OR IGNORE INTO gb_queue VALUES(?,?,?,0,?)',(uid,game,identity['region'],int(time.time())));return {'match':pair(d,game,identity['region'])}
  if action=='queue_leave':d.execute('DELETE FROM gb_queue WHERE uid=?',(uid,));return {'ok':True}
  if action=='notices_read':d.execute('UPDATE gb_notices SET seen=1 WHERE uid=?',(uid,));return {'ok':True}
  if action=='sanction':
   authorised(d,uid);target=str(b.get('uid',''));game=b.get('game');reason=str(b.get('reason','')).strip();until=b.get('until')
   if not d.execute('SELECT 1 FROM game_profiles WHERE uid=?',(target,)).fetchone() or game not in __import__('gaming').GAMES or type(until)!=int or not int(time.time())<=until<=time.time()+30*86400 or len(reason)<5:raise ValueError('Choose player, game, expiry (up to 30 days) and reason')
   old=row(d,'SELECT * FROM gb_sanctions WHERE uid=? AND game=?',(target,game));d.execute('INSERT OR REPLACE INTO gb_sanctions VALUES(?,?,?,?)',(target,game,until,reason));d.execute('DELETE FROM gb_queue WHERE uid=?',(target,));event(d,'sanction',uid,'sanction_updated',old=old,new=b,reason=reason);notice(d,target,'Gaming eligibility changed: '+reason);return {'ok':True}
  if action=='review':
   authorised(d,uid);m=row(d,'SELECT * FROM gb_matches WHERE id=?',(b.get('match'),))
   if not m or uid in (m['a'],m['b']) or m['state'] not in ('review','disputed'):raise PermissionError('Only an independent administrator may review this unresolved match')
   if not d.execute('SELECT 1 FROM gb_evidence WHERE match=? AND image IS NOT NULL',(m['id'],)).fetchone():raise ValueError('Evidence is required for review')
   reason=str(b.get('reason','')).strip();a,z=b.get('a'),b.get('b')
   if len(reason)<10 or any(type(v)!=int or not 0<=v<=99 for v in (a,z)):raise ValueError('Enter scores and a reason')
   verify(d,m,a,z,uid,reason);return {'ok':True}
  if action in ('schedule_propose','schedule_confirm','fixture_checkin'):
   f=row(d,'SELECT * FROM fixtures WHERE id=?',(b.get('fixture'),))
   if not f or uid not in (f['a'],f['b']):raise PermissionError('Only scheduled opponents may agree this time')
   if f['state'] in ('confirmed','void'):raise ValueError('This fixture is closed')
   side='a' if uid==f['a'] else 'b';schedule=row(d,'SELECT * FROM gb_schedule WHERE fixture=?',(f['id'],));league=row(d,'SELECT * FROM leagues WHERE id=?',(f['league'],));rules=json.loads(league['policy_snapshot'] or current(d)['config'])
   if action=='schedule_propose':
    at=b.get('at')
    if type(at)!=int or not max(time.time()+60,f['opens'])<=at<f['due']:raise ValueError('Choose a future time within the fixture window')
    if schedule and schedule['scheduled'] and (schedule['reschedules']>=rules['reschedules'] or time.time()>schedule['scheduled']-rules['checkin_seconds']):raise ValueError('The reschedule limit or cutoff was reached')
    league=row(d,'SELECT game FROM leagues WHERE id=?',(f['league'],))
    for player in (f['a'],f['b']):
     identity=row(d,'SELECT availability FROM gb_game_ids WHERE uid=? AND game=?',(player,league['game']))
     if not identity or not any(slot['start']<=at<slot['end'] for slot in json.loads(identity['availability'])):raise ValueError('Both players must register overlapping availability for this time')
    old=schedule
    if not schedule:d.execute('INSERT INTO gb_schedule(fixture,proposer,proposed) VALUES(?,?,?)',(f['id'],uid,at))
    else:d.execute('UPDATE gb_schedule SET proposer=?,proposed=?,confirmed_a=0,confirmed_b=0 WHERE fixture=?',(uid,at,f['id']))
    d.execute('UPDATE gb_schedule SET confirmed_'+side+'=1 WHERE fixture=?',(f['id'],));event(d,f['id'],uid,'schedule_proposed',old=old,new={'at':at});notice(d,f['b'] if side=='a' else f['a'],'Your opponent proposed a time. Confirm it or propose another overlapping time.')
   elif action=='schedule_confirm':
    if not schedule or not schedule['proposed'] or time.time()>=schedule['proposed']:raise ValueError('No future proposal is available')
    d.execute('UPDATE gb_schedule SET confirmed_'+side+'=1 WHERE fixture=?',(f['id'],));new=row(d,'SELECT * FROM gb_schedule WHERE fixture=?',(f['id'],))
    if new['confirmed_a'] and new['confirmed_b']:
     changes=1 if new['scheduled'] and new['scheduled']!=new['proposed'] else 0
     if new['reschedules']+changes>rules['reschedules']:raise ValueError('Reschedule allowance exceeded')
     d.execute('UPDATE gb_schedule SET scheduled=proposed,proposed=NULL,reschedules=reschedules+?,ready_a=0,ready_b=0,reminded=0 WHERE fixture=?',(changes,f['id']))
    event(d,f['id'],uid,'schedule_confirmed',old=schedule,new=new)
   else:
    if not schedule or not schedule['scheduled'] or not schedule['scheduled']-rules['checkin_seconds']<=time.time()<=schedule['scheduled']+rules['checkin_seconds']:raise ValueError('Check in near the mutually scheduled time')
    d.execute('UPDATE gb_schedule SET ready_'+side+'=1 WHERE fixture=?',(f['id'],));event(d,f['id'],uid,'fixture_checked_in')
   return {'ok':True}
  m=participant(d,uid,b.get('match'));side='a' if uid==m['a'] else 'b';rules=json.loads(m['rules'])
  if action=='accept':
   if m['state']!='proposed' or time.time()>m['deadline']:raise ValueError('The acceptance window is closed')
   d.execute('UPDATE gb_matches SET accepted_'+side+'=1 WHERE id=?',(m['id'],));updated=row(d,'SELECT * FROM gb_matches WHERE id=?',(m['id'],))
   if updated['accepted_a'] and updated['accepted_b']:d.execute("UPDATE gb_matches SET state='awaiting_checkin',deadline=? WHERE id=?",(int(time.time())+rules['checkin_seconds'],m['id']))
  elif action=='checkin':
   if m['state']!='awaiting_checkin' or time.time()>m['deadline']:raise ValueError('Check-in is closed')
   d.execute('UPDATE gb_matches SET ready_'+side+'=1 WHERE id=?',(m['id'],));updated=row(d,'SELECT * FROM gb_matches WHERE id=?',(m['id'],))
   if updated['ready_a'] and updated['ready_b']:d.execute("UPDATE gb_matches SET state='in_progress',deadline=? WHERE id=?",(int(time.time())+4*3600,m['id']))
  elif action=='complete':
   if m['state']!='in_progress':raise ValueError('The match has not started')
   d.execute("UPDATE gb_matches SET state='awaiting_results',deadline=? WHERE id=?",(int(time.time())+rules['result_seconds'],m['id']))
   for u in (m['a'],m['b']):notice(d,u,'Enter scores in the fixed player order. Preserve the final result screen until both reports are accepted.')
  elif action=='report':
   if m['state']!='awaiting_results' or time.time()>m['deadline']:raise ValueError('This result needs review; the submission window is closed')
   a,z=b.get('a'),b.get('b')
   if any(type(v)!=int or not 0<=v<=99 for v in (a,z)):raise ValueError('Enter whole-number scores')
   old=row(d,'SELECT * FROM gb_reports WHERE match=? AND uid=?',(m['id'],uid))
   if old:raise ValueError('Your independent report is already submitted')
   d.execute('INSERT INTO gb_reports VALUES(?,?,?,?)',(m['id'],uid,a,z));reports=[dict(r) for r in d.execute('SELECT * FROM gb_reports WHERE match=?',(m['id'],))]
   if len(reports)==2:
    if (reports[0]['a'],reports[0]['b'])==(reports[1]['a'],reports[1]['b']):verify(d,m,a,z,uid)
    else:
     d.execute("UPDATE gb_matches SET state='disputed',deadline=? WHERE id=?",(int(time.time())+rules['evidence_seconds'],m['id']))
     for u in (m['a'],m['b']):notice(d,u,'Scores disagree. Both players may submit screenshots showing final score and both gaming IDs.')
  elif action=='evidence':
   if m['state'] not in ('disputed','review'):raise ValueError('Evidence is collected for disputed or reviewed matches')
   import gaming
   raw,mime=gaming.image(b);digest=hashlib.sha256(raw).hexdigest();other=d.execute('SELECT 1 FROM gb_evidence WHERE digest=? AND (match!=? OR uid!=?)',(digest,m['id'],uid)).fetchone()
   if other:raise ValueError('This evidence was already used')
   if d.execute('SELECT 1 FROM gb_evidence WHERE match=? AND uid=?',(m['id'],uid)).fetchone():raise ValueError('Original evidence cannot be overwritten')
   d.execute('INSERT INTO gb_evidence VALUES(?,?,?,?,?,?,NULL)',(m['id'],uid,raw,mime,digest,str(b.get('reading',''))[:6000]))
  elif action=='comment':
   text=str(b.get('text','')).strip()
   if not 1<=len(text)<=1000:raise ValueError('Message must be under 1000 characters')
   d.execute('INSERT INTO gb_room_messages(match,uid,text,created) VALUES(?,?,?,?)',(m['id'],uid,text,int(time.time())))
  elif action=='cancel':
   if m['state'] not in ('proposed','awaiting_checkin'):raise ValueError('Active matches cannot be silently cancelled')
   d.execute("UPDATE gb_matches SET state='cancelled' WHERE id=?",(m['id'],))
  else:raise ValueError('Unknown match action')
  event(d,m['id'],uid,action,old={'state':m['state']},new={k:v for k,v in b.items() if k not in ('image','reading')});return {'ok':True}

def tick(server,now=None):
 now=int(time.time()) if now is None else now
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  for m in [dict(r) for r in d.execute("SELECT * FROM gb_matches WHERE deadline<? AND state IN ('proposed','awaiting_checkin','in_progress','awaiting_results')",(now,))]:
   if m['state'] in ('in_progress','awaiting_results'):
    d.execute("UPDATE gb_matches SET state='review',deadline=? WHERE id=?",(now+json.loads(m['rules'])['evidence_seconds'],m['id']))
    for u in (m['a'],m['b']):notice(d,u,'Result deadline reached. Review is required; silence does not award a win.')
   else:
    d.execute("UPDATE gb_matches SET state='cancelled' WHERE id=?",(m['id'],))
    for side in ('a','b'):
     u=m[side];ready=m['ready_'+side] if m['state']=='awaiting_checkin' else m['accepted_'+side]
     notice(d,u,'Match proposal expired. No rating change.')
     if ready:
      identity=row(d,'SELECT * FROM gb_game_ids WHERE uid=? AND game=?',(u,m['game']))
      if identity:d.execute('INSERT OR IGNORE INTO gb_queue VALUES(?,?,?,1,?)',(u,m['game'],identity['region'],now))
   event(d,m['id'],'system','deadline_processed',old=m['state'],new='review' if m['state'] in ('in_progress','awaiting_results') else 'cancelled')
  for group in d.execute('SELECT DISTINCT game,region FROM gb_queue').fetchall():pair(d,group['game'],group['region'])
  for scheduled in [dict(r) for r in d.execute("SELECT s.*,f.a,f.b,l.game,l.policy_snapshot FROM gb_schedule s JOIN fixtures f ON f.id=s.fixture JOIN leagues l ON l.id=f.league WHERE s.reminded=0 AND s.scheduled IS NOT NULL AND f.state NOT IN ('confirmed','void','walkover')")]:
   rules=json.loads(scheduled['policy_snapshot'] or current(d)['config'])
   if scheduled['scheduled']-rules['reminder_seconds']>now:continue
   for u in (scheduled['a'],scheduled['b']):
    identity=row(d,'SELECT reminders FROM gb_game_ids WHERE uid=? AND game=?',(u,scheduled['game']))
    if identity and identity['reminders']:notice(d,u,'Your mutually scheduled league match is approaching. Open its fixture to check in.')
   d.execute('UPDATE gb_schedule SET reminded=1 WHERE fixture=?',(scheduled['fixture'],))
  for pending in [dict(r) for r in d.execute("SELECT f.id,f.a,f.b,l.policy_snapshot,MIN(a.time) submitted FROM fixtures f JOIN leagues l ON l.id=f.league JOIN game_audit a ON a.fixture=f.id AND a.action='submitted' WHERE f.state='pending' AND l.verification='typed' GROUP BY f.id")]:
   rules=json.loads(pending['policy_snapshot'] or current(d)['config'])
   if pending['submitted']+rules['result_seconds']<now:
    d.execute("UPDATE fixtures SET state='disputed' WHERE id=?",(pending['id'],));event(d,pending['id'],'system','competition_submission_expired',reason='Silence is not proof; evidence and independent review required')
    for u in (pending['a'],pending['b']):notice(d,u,'League score response deadline passed. Both players may supply evidence for review.')
  for expired_fixture in [dict(r) for r in d.execute("SELECT r.fixture FROM gb_comp_retention r JOIN fixtures f ON f.id=r.fixture WHERE r.expires<? AND f.state='confirmed'",(now,))]:
   d.execute('UPDATE game_reports SET image=NULL WHERE fixture=?',(expired_fixture['fixture'],));d.execute('DELETE FROM gb_comp_retention WHERE fixture=?',(expired_fixture['fixture'],));event(d,expired_fixture['fixture'],'system','ordinary_competition_evidence_expired')
  expired=[dict(r) for r in d.execute('SELECT e.match,e.uid FROM gb_evidence e JOIN gb_matches m ON m.id=e.match WHERE e.image IS NOT NULL AND e.expires<? AND m.state=\'verified\'',(now,))]
  for e in expired:d.execute('UPDATE gb_evidence SET image=NULL WHERE match=? AND uid=?',(e['match'],e['uid']));event(d,e['match'],'system','ordinary_evidence_expired',new={'uid':e['uid']})

def rate_competition_results(d,league):
 for f in [dict(r) for r in d.execute("SELECT * FROM fixtures WHERE league=? AND state='confirmed' AND id NOT IN (SELECT fixture FROM gb_rating_events)",(league['id'],))]:
  game=league['game'];old={}
  for uid in (f['a'],f['b']):
   d.execute('INSERT OR IGNORE INTO gb_ratings(uid,game) VALUES(?,?)',(uid,game));old[uid]=row(d,'SELECT * FROM gb_ratings WHERE uid=? AND game=?',(uid,game))
  for uid,other,own,theirs in [(f['a'],f['b'],f['score_a'],f['score_b']),(f['b'],f['a'],f['score_b'],f['score_a'])]:
   score=1 if own>theirs else .5 if own==theirs else 0;expected=1/(1+10**((old[other]['rating']-old[uid]['rating'])/400));rating=round(old[uid]['rating']+24*(score-expected),2)
   d.execute('UPDATE gb_ratings SET rating=?,played=played+1,activity=activity+1 WHERE uid=? AND game=?',(rating,uid,game))
  d.execute('INSERT OR IGNORE INTO gb_comp_retention VALUES(?,?)',(f['id'],int(time.time())+json.loads(league['policy_snapshot'] or current(d)['config'])['retention_seconds']));d.execute('INSERT INTO gb_rating_events VALUES(?,?)',(f['id'],int(time.time())));event(d,f['id'],'system','competition_rating_updated',old=old,reason='Confirmed played result; no walkover rating')

def dispatch_notices(server):
 if not getattr(server.push,'enabled',False):return
 pending=[];now=int(time.time())
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE')
  for n in [dict(r) for r in d.execute('SELECT n.* FROM gb_notices n LEFT JOIN gb_notice_delivery p ON p.id=n.id WHERE n.seen=0 AND n.created>? AND COALESCE(p.delivered,0)=0 AND COALESCE(p.attempts,0)<3 AND COALESCE(p.next_attempt,0)<=? ORDER BY n.id LIMIT 20',(now-3600,now))]:
   targets=[r[0] for r in d.execute('SELECT token FROM push_devices p JOIN sessions s ON s.token_hash=p.session_hash AND s.user_id=p.user_id WHERE p.user_id=?',(n['uid'],))]
   if not targets:continue
   d.execute('INSERT INTO gb_notice_delivery(id,attempts,next_attempt) VALUES(?,1,?) ON CONFLICT(id) DO UPDATE SET attempts=attempts+1,next_attempt=excluded.next_attempt',(n['id'],now+300));pending.append((n,targets))
 if not pending:return
 def send():
  for n,targets in pending:
   success=False
   for token in targets:
    try:server.push.send(token,{'event':'gamebox_notice','notice_id':str(n['id']),'recipient':n['uid'],'expires_at':str(now+600)});success=True
    except Exception as error:print('Gamebox notice push failed: '+type(error).__name__,flush=True)
   if success:
    with server.db() as d:d.execute('UPDATE gb_notice_delivery SET delivered=1 WHERE id=?',(n['id'],))
 import threading
 threading.Thread(target=send,daemon=True).start()
