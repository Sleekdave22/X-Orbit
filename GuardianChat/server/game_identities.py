"""Controlled lifecycle for existing per-game identities, preserving historical snapshots."""
import json,time,uuid,unicodedata,re

def normalize(value):return unicodedata.normalize('NFKC',value).strip().casefold()
def init(server):
 with server.db() as d:
  d.executescript('''CREATE TABLE IF NOT EXISTS gb_identity_meta(uid TEXT,game TEXT,state TEXT NOT NULL DEFAULT 'active',nickname TEXT NOT NULL DEFAULT '',platform TEXT NOT NULL DEFAULT 'unspecified',country TEXT NOT NULL DEFAULT '',verification TEXT NOT NULL DEFAULT 'unverified',visible INTEGER NOT NULL DEFAULT 0,PRIMARY KEY(uid,game));
  CREATE TABLE IF NOT EXISTS gb_identity_claims(game TEXT,normalized TEXT,uid TEXT NOT NULL,PRIMARY KEY(game,normalized));
  CREATE TABLE IF NOT EXISTS gb_identity_requests(id TEXT PRIMARY KEY,uid TEXT,game TEXT,kind TEXT,new_id TEXT,reason TEXT,challenge TEXT,state TEXT DEFAULT 'pending',reviewer TEXT,note TEXT DEFAULT '',created INTEGER,reviewed INTEGER);
  CREATE UNIQUE INDEX IF NOT EXISTS gb_identity_pending ON gb_identity_requests(uid,game,kind) WHERE state='pending';
  CREATE TABLE IF NOT EXISTS gb_identity_migrations(version INTEGER PRIMARY KEY,created INTEGER);''')
  if not d.execute('SELECT 1 FROM gb_identity_migrations WHERE version=1').fetchone():
   for i in d.execute('SELECT i.*,p.tag FROM gb_game_ids i JOIN game_profiles p ON p.uid=i.uid ORDER BY i.uid').fetchall():
    d.execute('INSERT OR IGNORE INTO gb_identity_meta(uid,game,nickname) VALUES(?,?,?)',(i['uid'],i['game'],i['tag']))
    owner=d.execute('SELECT uid FROM gb_identity_claims WHERE game=? AND normalized=?',(i['game'],normalize(i['game_id']))).fetchone()
    if owner and owner[0]!=i['uid']:
     d.execute("UPDATE gb_identity_meta SET state='conflict' WHERE game=? AND uid IN (?,?)",(i['game'],i['uid'],owner[0]))
    else:d.execute('INSERT OR IGNORE INTO gb_identity_claims VALUES(?,?,?)',(i['game'],normalize(i['game_id']),i['uid']))
   d.execute('INSERT INTO gb_identity_migrations VALUES(1,?)',(int(time.time()),))
def meta(d,uid,game):
 r=d.execute('SELECT * FROM gb_identity_meta WHERE uid=? AND game=?',(uid,game)).fetchone();return dict(r) if r else None
def visible(d,viewer,target,game):
 import social
 m=meta(d,target,game)
 return bool(m and m['state']=='active' and m['visible'] and not social.blocked(d,viewer,target) and social.public(d,viewer,target)['can_view_lists'])
def commitments(d,uid,game):
 if d.execute("SELECT 1 FROM sl_registrations r JOIN sl_leagues l ON l.id=r.league WHERE r.uid=? AND l.game=? AND l.state IN ('REGISTRATION_OPEN','REGISTRATION_CLOSED','ACTIVE','FINALISING')",(uid,game)).fetchone():return True
 return bool(d.execute('SELECT 1 FROM gb_queue WHERE uid=? AND game=?',(uid,game)).fetchone() or d.execute("SELECT 1 FROM gb_matches WHERE game=? AND (a=? OR b=?) AND state NOT IN ('verified','cancelled')",(game,uid,uid)).fetchone() or d.execute("SELECT 1 FROM league_members m JOIN leagues l ON l.id=m.league WHERE m.uid=? AND l.game=? AND l.state!='finished'",(uid,game)).fetchone() or d.execute("SELECT 1 FROM gb_season_entries e JOIN gb_seasons s ON s.id=e.season WHERE e.uid=? AND s.game=? AND s.state IN ('enrolling','review','active')",(uid,game)).fetchone())
def claim(d,uid,game,gid):
 owner=d.execute('SELECT uid FROM gb_identity_claims WHERE game=? AND normalized=?',(game,normalize(gid))).fetchone()
 if owner and owner[0]!=uid:raise ValueError('This game ID is already registered to another active account')
 # Preserve legacy records; collision detection must include unmigrated or conflicting IDs.
 for r in d.execute("SELECT i.uid,i.game_id FROM gb_game_ids i LEFT JOIN gb_identity_meta m ON m.uid=i.uid AND m.game=i.game WHERE i.game=? AND i.uid!=? AND COALESCE(m.state,'active')!='disabled'",(game,uid)):
  if normalize(r['game_id'])==normalize(gid):raise ValueError('This game ID is already registered; review is required')
 d.execute('INSERT OR REPLACE INTO gb_identity_claims VALUES(?,?,?)',(game,normalize(gid),uid))
def save(d,uid,b):
 import gaming,gamebox_core
 game=b.get('game')
 if game not in gaming.GAMES or not d.execute('SELECT 1 FROM game_profiles WHERE uid=? AND adult=1',(uid,)).fetchone():raise ValueError('Create your adult gaming profile and choose a supported game')
 old=gamebox_core.row(d,'SELECT * FROM gb_game_ids WHERE uid=? AND game=?',(uid,game));m=meta(d,uid,game)
 gid=b.get('game_id','');region=b.get('region','');tz=b.get('tz','');slots=b.get('availability',[])
 if any(not isinstance(x,str) for x in (gid,region,tz)) or not 2<=len(gid.strip())<=60 or not 1<=len(region.strip())<=40 or not 1<=len(tz)<=60 or type(slots)!=list or len(slots)>14:raise ValueError('Enter game ID, region, time zone and availability')
 gid=unicodedata.normalize('NFKC',gid).strip()
 if any(ord(x)<32 for x in gid):raise ValueError('Use a valid game ID')
 from zoneinfo import ZoneInfo
 try:ZoneInfo(tz)
 except Exception:raise ValueError('Use a valid time-zone name')
 for slot in slots:
  if type(slot)!=dict or set(slot)!={'start','end'} or any(type(slot[k]) is not int for k in ('start','end')) or not time.time()<slot['start']<slot['end']<=time.time()+60*86400:raise ValueError('Availability must contain future start/end times')
 if old and normalize(old['game_id'])!=normalize(gid):raise ValueError('Use Change Gaming ID for a reviewed change; saved history is preserved')
 if m and m['state']=='conflict':raise ValueError('This identity has a legacy conflict requiring administrator review')
 if m and m['state']=='disabled' and commitments(d,uid,game):raise ValueError('Finish active commitments before reactivating this game')
 nickname=b.get('nickname',(m or {}).get('nickname') or d.execute('SELECT tag FROM game_profiles WHERE uid=?',(uid,)).fetchone()[0]);platform=b.get('platform',(m or {}).get('platform','unspecified'));country=b.get('country',(m or {}).get('country',''));show=b.get('visible',bool((m or {}).get('visible',False)))
 if not isinstance(nickname,str) or not 2<=len(nickname.strip())<=30 or platform not in ('unspecified','mobile','console','pc','crossplay') or not isinstance(country,str) or country and not re.fullmatch('[A-Z]{2}',country) or type(show) is not bool:raise ValueError('Check gaming nickname, platform, two-letter country code and ranking visibility')
 claim(d,uid,game,gid)
 d.execute('INSERT INTO gb_game_ids(uid,game,game_id,region,tz,availability,reminders) VALUES(?,?,?,?,?,?,?) ON CONFLICT(uid,game) DO UPDATE SET region=excluded.region,tz=excluded.tz,availability=excluded.availability,reminders=excluded.reminders',(uid,game,gid,region.strip(),tz,json.dumps(slots),int(b.get('reminders',True) is True)))
 d.execute("INSERT INTO gb_identity_meta(uid,game,state,nickname,platform,country,visible) VALUES(?,?,'active',?,?,?,?) ON CONFLICT(uid,game) DO UPDATE SET state='active',nickname=excluded.nickname,platform=excluded.platform,country=excluded.country,visible=excluded.visible",(uid,game,nickname.strip(),platform,country,int(show)))
 gamebox_core.event(d,'identity',uid,'game_identity_saved',old=old,new={'game':game,'game_id':gid});return {'saved':True}
def post(server,uid,action,b):
 import gamebox_core
 with server.db() as d:
  d.execute('BEGIN IMMEDIATE');gamebox_core.current(d)
  if action=='review':
   gamebox_core.authorised(d,uid);r=gamebox_core.row(d,'SELECT * FROM gb_identity_requests WHERE id=?',(b.get('request'),));decision=b.get('decision');note=b.get('note','')
   if not r or r['state']!='pending' or r['uid']==uid:raise PermissionError('An independent administrator must review a pending request')
   if decision not in ('approve','decline') or not isinstance(note,str) or not 10<=len(note.strip())<=1000:raise ValueError('Explain the verification evidence and decision')
   m=meta(d,r['uid'],r['game'])
   if not m or m['state'] not in ('active','conflict') or m['state']=='conflict' and r['kind']!='change':raise ValueError('Identity must be active, or have a conflict-resolution change request')
   if decision=='approve':
    if r['kind']=='change':
     if commitments(d,r['uid'],r['game']):raise ValueError('The player has active registrations, queue or matches')
     claim(d,r['uid'],r['game'],r['new_id']);d.execute('DELETE FROM gb_identity_claims WHERE uid=? AND game=? AND normalized!=?',(r['uid'],r['game'],normalize(r['new_id'])));d.execute('UPDATE gb_game_ids SET game_id=? WHERE uid=? AND game=?',(r['new_id'],r['uid'],r['game']));d.execute("UPDATE gb_identity_meta SET verification='unverified',state='active' WHERE uid=? AND game=?",(r['uid'],r['game']))
    else:d.execute("UPDATE gb_identity_meta SET verification='manual_reviewed' WHERE uid=? AND game=?",(r['uid'],r['game']))
   elif r['kind']=='verification':d.execute("UPDATE gb_identity_meta SET verification='unverified' WHERE uid=? AND game=?",(r['uid'],r['game']))
   d.execute('UPDATE gb_identity_requests SET state=?,reviewer=?,note=?,reviewed=? WHERE id=?',('approved' if decision=='approve' else 'declined',uid,note.strip(),int(time.time()),r['id']));gamebox_core.event(d,'identity',uid,'identity_request_reviewed',old=r,new={'decision':decision},reason=note.strip());return {'saved':True}
  if action=='save':return save(d,uid,b)
  game=b.get('game');m=meta(d,uid,game)
  if not m or m['state']!='active' and not (m['state']=='conflict' and action=='change'):raise ValueError('Register an active game identity first')
  if action=='disable':
   if commitments(d,uid,game):raise ValueError('Finish or withdraw active registrations, queue and matches before removing this game')
   if d.execute("SELECT 1 FROM gb_identity_requests WHERE uid=? AND game=? AND state='pending'",(uid,game)).fetchone():raise ValueError('Resolve pending identity requests before removing this game')
   d.execute("UPDATE gb_identity_meta SET state='disabled',visible=0 WHERE uid=? AND game=?",(uid,game));d.execute('DELETE FROM gb_identity_claims WHERE uid=? AND game=?',(uid,game));gamebox_core.event(d,'identity',uid,'game_registration_disabled',new={'game':game});return {'saved':True}
  if action not in ('change','verification'):raise ValueError('Unknown identity action')
  reason=b.get('reason','');new_id=unicodedata.normalize('NFKC',b.get('new_id','')).strip() if isinstance(b.get('new_id',''),str) else ''
  if not isinstance(reason,str) or not 10<=len(reason.strip())<=1000:raise ValueError('Explain the change or the ownership evidence in 10–1000 characters')
  if d.execute("SELECT COUNT(*) FROM gb_identity_requests WHERE uid=? AND created>?",(uid,int(time.time())-3600)).fetchone()[0]>=5:raise ValueError('Identity request limit reached; try later')
  if d.execute("SELECT 1 FROM gb_identity_requests WHERE uid=? AND game=? AND state='pending'",(uid,game)).fetchone():raise ValueError('A request for this game is already pending')
  if action=='change':
   if not 2<=len(new_id)<=60 or any(ord(x)<32 for x in new_id) or commitments(d,uid,game):raise ValueError('Finish active commitments and provide a valid new gaming ID')
   current_id=d.execute('SELECT game_id FROM gb_game_ids WHERE uid=? AND game=?',(uid,game)).fetchone()[0]
   if m['state']!='conflict' and normalize(new_id)==normalize(current_id):raise ValueError('Provide a different gaming ID')
   # Validate without reserving an unapproved new identity.
   if d.execute('SELECT 1 FROM gb_identity_claims WHERE game=? AND normalized=? AND uid!=?',(game,normalize(new_id),uid)).fetchone():raise ValueError('Requested gaming ID is already in use')
  rid=uuid.uuid4().hex;challenge=uuid.uuid4().hex[:12];kind='change' if action=='change' else 'verification'
  d.execute('INSERT INTO gb_identity_requests(id,uid,game,kind,new_id,reason,challenge,created) VALUES(?,?,?,?,?,?,?,?)',(rid,uid,game,kind,new_id,reason.strip(),challenge,int(time.time())))
  if kind=='verification':d.execute("UPDATE gb_identity_meta SET verification='pending_manual_review' WHERE uid=? AND game=?",(uid,game))
  gamebox_core.event(d,'identity',uid,'identity_request_created',new={'game':game,'request':rid,'kind':kind});return {'id':rid,'challenge':challenge,'note':'Manual review only; no publisher API or automated ownership verification is connected.'}
def get(server,uid,action,q):
 import gamebox_core
 with server.db() as d:
  if action=='review_queue':gamebox_core.authorised(d,uid);return {'requests':[dict(r) for r in d.execute("SELECT * FROM gb_identity_requests WHERE state='pending' ORDER BY created LIMIT 100")]}
  if action!='mine':raise ValueError('Unknown identity action')
  return {'identities':[dict(r) for r in d.execute('SELECT i.*,m.state,m.nickname,m.platform,m.country,m.verification,m.visible FROM gb_game_ids i JOIN gb_identity_meta m ON m.uid=i.uid AND m.game=i.game WHERE i.uid=?',(uid,))],'requests':[dict(r) for r in d.execute('SELECT * FROM gb_identity_requests WHERE uid=? ORDER BY created DESC LIMIT 50',(uid,))]}
