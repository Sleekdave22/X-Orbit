import unittest,urllib.error,time,json
from unittest.mock import patch
import test_server,gamebox_core
from server import account_qr
class CoreTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 def players(self):
  users=[self.register(name) for name in ('Owner','Player','Reviewer')]
  with self.server.db() as d:d.execute('INSERT INTO game_admin VALUES(?)',(users[0]['id'],))
  for u in users:
   self.call('/gaming/profile',{'tag':u['name'],'game_id':u['id'],'adult':True},u['token'])
   self.call('/gamebox/identity',{'game':'efootball','game_id':'game-'+u['id'],'region':'Nigeria','tz':'Africa/Lagos','availability':[]},u['token'])
  return users
 def match(self):
  us=self.players()
  for u in us[:2]:self.call('/gamebox/queue',{'game':'efootball'},u['token'])
  m=self.call('/gamebox/summary',token=us[0]['token'])['matches'][0]
  return us,m
 def ready(self):
  us,m=self.match()
  for u in us[:2]:self.call('/gamebox/accept',{'match':m['id']},u['token'])
  for u in us[:2]:self.call('/gamebox/checkin',{'match':m['id']},u['token'])
  self.call('/gamebox/complete',{'match':m['id']},us[0]['token']);return us,m
 def test_dual_acceptance_checkin_and_no_evidence_routine(self):
  us,m=self.match();self.call('/gamebox/accept',{'match':m['id']},us[0]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/checkin',{'match':m['id']},us[0]['token'])
  self.call('/gamebox/accept',{'match':m['id']},us[1]['token'])
  for u in us[:2]:self.call('/gamebox/checkin',{'match':m['id']},u['token'])
  self.call('/gamebox/complete',{'match':m['id']},us[0]['token'])
  self.call('/gamebox/report',{'match':m['id'],'a':2,'b':1},us[0]['token'])
  pending=self.call('/gamebox/summary',token=us[1]['token']);self.assertNotIn('a',pending['matches'][0]['reports'][0]);self.assertTrue(pending['matches'][0]['reports'][0]['submitted'])
  self.call('/gamebox/report',{'match':m['id'],'a':2,'b':1},us[1]['token'])
  summary=self.call('/gamebox/summary',token=us[0]['token']);self.assertEqual(summary['matches'][0]['state'],'verified');self.assertEqual(summary['ratings'][0]['played'],1)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/report',{'match':m['id'],'a':9,'b':0},us[0]['token'])
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_evidence').fetchone()[0],0)
 def test_config_permissions_revision_and_persistence(self):
  us=self.players();studio=self.call('/gamebox/studio',token=us[0]['token']);v=studio['published'];config=json.loads(v['config']);config['theme']['radius']=10
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/studio_save',{'base':v['id'],'config':config},us[1]['token'])
  self.call('/gamebox/studio_save',{'base':v['id'],'config':config},us[0]['token']);self.call('/gamebox/studio_publish',{'reason':'Update supported radius'},us[0]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/studio_save',{'base':v['id'],'config':config},us[0]['token'])
  gamebox_core.init(self.server);self.assertEqual(self.call('/gamebox/summary',token=us[1]['token'])['config']['theme']['radius'],10)
  self.call('/gamebox/studio_rollback',{'version':v['id'],'reason':'Restore earlier styling'},us[0]['token']);self.assertEqual(self.call('/gamebox/summary',token=us[1]['token'])['config']['theme']['radius'],8)
 def test_expired_proposal_requeues_ready_player_without_rating(self):
  us,m=self.match();self.call('/gamebox/accept',{'match':m['id']},us[0]['token'])
  gamebox_core.tick(self.server,m['deadline']+1)
  s=self.call('/gamebox/summary',token=us[0]['token']);self.assertEqual(s['matches'][0]['state'],'cancelled');self.assertEqual(s['queue']['priority'],1);self.assertEqual(s['ratings'],[])
 def test_dispute_evidence_is_private_and_cannot_be_overwritten(self):
  us,m=self.ready()
  self.call('/gamebox/report',{'match':m['id'],'a':2,'b':1},us[0]['token']);self.call('/gamebox/report',{'match':m['id'],'a':1,'b':2},us[1]['token'])
  with patch('gaming.scan',return_value={'text':'Original score and IDs','available':True}):self.call('/gamebox/evidence',{'match':m['id'],'image':account_qr('proof')},us[0]['token'])
  with patch('gaming.scan',return_value={'text':'replacement','available':True}):
   with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/evidence',{'match':m['id'],'image':account_qr('replacement')},us[0]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/evidence?match='+m['id']+'&player='+us[0]['id'],token=us[2]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/review',{'match':m['id'],'a':2,'b':1,'reason':'Own match cannot be reviewed'},us[0]['token'])
  with self.server.db() as d:d.execute('DELETE FROM game_admin');d.execute('INSERT INTO game_admin VALUES(?)',(us[2]['id'],))
  self.call('/gamebox/review',{'match':m['id'],'a':2,'b':1,'reason':'Evidence reviewed against both official IDs'},us[2]['token'])
  with self.server.db() as d:e=d.execute('SELECT expires FROM gb_evidence WHERE match=?',(m['id'],)).fetchone()[0]
  gamebox_core.tick(self.server,e+1)
  with self.server.db() as d:self.assertIsNone(d.execute('SELECT image FROM gb_evidence WHERE match=?',(m['id'],)).fetchone()[0]);self.assertTrue(d.execute("SELECT 1 FROM gb_events WHERE action='ordinary_evidence_expired'").fetchone())
 def test_deadline_does_not_award_unanswered_result(self):
  us,m=self.ready();self.call('/gamebox/report',{'match':m['id'],'a':7,'b':0},us[0]['token'])
  s=self.call('/gamebox/summary',token=us[0]['token']);gamebox_core.tick(self.server,s['matches'][0]['deadline']+1)
  s=self.call('/gamebox/summary',token=us[0]['token']);self.assertEqual(s['matches'][0]['state'],'review');self.assertEqual(s['ratings'],[])
 def test_ten_player_fixtures_schedule_and_typed_result(self):
  us=self.players()
  for i in range(7):
   u=self.register('Extra'+str(i));self.call('/gaming/profile',{'tag':u['name'],'game_id':u['id'],'adult':True},u['token']);us.append(u)
  at=int(time.time())+120
  for u in us:self.call('/gamebox/identity',{'game':'efootball','game_id':'game-'+u['id'],'region':'Nigeria','tz':'Africa/Lagos','availability':[{'start':at-60,'end':at+3600}]},u['token'])
  l=self.call('/gaming/create',{'name':'Ten player group','game':'efootball','capacity':10,'round_days':3},us[0]['token'])['id']
  for u in us:self.call('/gaming/join',{'league':l},u['token'])
  self.call('/gaming/start',{'league':l},us[0]['token']);state=self.call('/gaming/summary?league='+l,token=us[0]['token']);self.assertEqual(len(state['fixtures']),45);self.assertEqual(max(f['round'] for f in state['fixtures']),9)
  f=state['fixtures'][0];lookup={u['id']:u for u in us};a,b=lookup[f['a']],lookup[f['b']]
  self.call('/gamebox/schedule_propose',{'fixture':f['id'],'at':at},a['token']);self.call('/gamebox/schedule_confirm',{'fixture':f['id']},b['token'])
  for u in (a,b):self.call('/gamebox/fixture_checkin',{'fixture':f['id']},u['token'])
  for u in (a,b):self.call('/gaming/report',{'league':l,'fixture':f['id'],'score_a':2,'score_b':1},u['token'])
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_rating_events').fetchone()[0],1)
  result=self.call('/gaming/summary?league='+l,token=a['token']);self.assertEqual(result['fixtures'][0]['state'],'confirmed')
 def test_simulator_and_configuration_guardrails(self):
  us=self.players();result=self.call('/gamebox/simulate',{'entrants':1000,'group_size':10,'round_days':3},us[0]['token']);self.assertEqual(result['groups'],100);self.assertEqual(result['fixtures'],4500);self.assertEqual(result['estimated_days'],27)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/simulate',{'entrants':1000,'group_size':10,'round_days':3},us[1]['token'])
  info=self.call('/gamebox/studio',token=us[0]['token']);config=json.loads(info['published']['config']);config['fake_user_count']=999999
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/studio_save',{'base':info['published']['id'],'config':config},us[0]['token'])
 def test_documented_walkover_changes_points_but_not_rating(self):
  us=self.players()
  for i in range(5):
   u=self.register('League'+str(i));self.call('/gaming/profile',{'tag':u['name'],'game_id':u['id'],'adult':True},u['token']);us.append(u)
  l=self.call('/gaming/create',{'name':'No show policy test','game':'efootball'},us[0]['token'])['id']
  for u in us:self.call('/gaming/join',{'league':l},u['token'])
  self.call('/gaming/start',{'league':l},us[0]['token']);state=self.call('/gaming/summary?league='+l,token=us[0]['token']);f=next(f for f in state['fixtures'] if us[0]['id'] not in (f['a'],f['b']))
  with self.server.db() as d:d.execute('INSERT INTO gb_schedule(fixture,scheduled,ready_a,ready_b) VALUES(?,?,1,0)',(f['id'],int(time.time())-1000))
  self.call('/gamebox/walkover',{'fixture':f['id'],'reason':'Scheduled opponent did not check in by the deadline'},us[0]['token'])
  table=self.call('/gaming/summary?league='+l,token=us[0]['token'])['table'];self.assertEqual(next(r for r in table if r['uid']==f['a'])['points'],3)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_ratings').fetchone()[0],0)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/walkover',{'fixture':f['id'],'reason':'Repeat no show award'},us[0]['token'])
 def test_notice_push_contains_no_scores_and_is_not_replayed(self):
  import threading
  us=self.players();self.call('/push/register',{'push_token':'test-notice-token-'+'b'*40},us[0]['token'])
  class FakePush:
   enabled=True
   def __init__(self):self.events=[];self.ready=threading.Event()
   def send(self,token,payload):self.events.append(payload);self.ready.set()
  push=FakePush();self.server.push=push
  with self.server.db() as d:gamebox_core.notice(d,us[0]['id'],'Private final score and gaming ID')
  gamebox_core.dispatch_notices(self.server);self.assertTrue(push.ready.wait(2));self.assertEqual(push.events[0]['event'],'gamebox_notice');self.assertNotIn('Private',str(push.events[0]));self.assertNotIn('score',push.events[0])
 def test_season_close_generates_groups_once(self):
  us=self.players()
  for i in range(17):
   u=self.register('Season'+str(i));self.call('/gaming/profile',{'tag':u['name'],'game_id':u['id'],'adult':True},u['token']);us.append(u)
  now=int(time.time())
  for u in us:self.call('/gamebox/identity',{'game':'efootball','game_id':'game-'+u['id'],'region':'Nigeria','tz':'Africa/Lagos','availability':[{'start':now+100,'end':now+3600}]},u['token'])
  season=self.call('/gamebox/season_create',{'name':'Season grouping test','game':'efootball','tier':0,'opens':now,'closes':now+120},us[0]['token'])['id']
  for u in us:self.call('/gamebox/season_register',{'season':season},u['token'])
  gamebox_core.tick(self.server,now+121);gamebox_core.tick(self.server,now+122)
  state=self.call('/gamebox/summary',token=us[0]['token']);self.assertEqual(state['seasons'][0]['state'],'active');self.assertEqual(len(state['seasons'][0]['groups']),2)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM fixtures').fetchone()[0],90);self.assertEqual(d.execute('SELECT COUNT(*) FROM league_members').fetchone()[0],20)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/season_register',{'season':season},us[0]['token'])
 def test_weekly_open_qualification_is_derived_from_verified_outcomes(self):
  us=self.players()
  with self.server.db() as d:
   rules=dict(gamebox_core.DEFAULT,weekly_min_matches=1,weekly_min_opponents=1);week=int(time.time())-100
   d.execute("INSERT INTO gb_matches(id,game,a,b,gid_a,gid_b,state,created,deadline,version,rules,verified,score_a,score_b) VALUES('q','efootball',?,?,?,?,'verified',?,?,1,?,?,2,1)",(us[1]['id'],us[2]['id'],'one','two',week,week,json.dumps(rules),int(time.time())))
   standings=gamebox_core.weekly(d,'efootball',week,rules);self.assertEqual(standings[0]['uid'],us[1]['id']);self.assertEqual(standings[0]['points'],3)
   self.assertEqual(gamebox_core.weekly(d,'fc_mobile',week,rules),[])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/qualified_cup',{'name':'No fake qualifiers','game':'efootball'},us[0]['token'])
if __name__=='__main__':unittest.main()
