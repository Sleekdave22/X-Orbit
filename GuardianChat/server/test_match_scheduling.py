import unittest,time,json,urllib.error,datetime as dt
from unittest.mock import patch
import test_server,test_gamebox_core,match_scheduling as ms,gamebox_core
class SchedulingTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 players=test_gamebox_core.CoreTest.players
 def setup_match(self):
  a,b,c=self.players();now=int(time.time());mid=__import__('uuid').uuid4().hex
  with self.server.db() as d:
   rules=gamebox_core.current(d);d.execute("INSERT INTO gb_matches(id,game,a,b,gid_a,gid_b,state,created,deadline,accepted_a,accepted_b,version,rules) VALUES(?,'efootball',?,?,?,?,'awaiting_checkin',?,?,1,1,?,?)",(mid,a['id'],b['id'],'a','b',now,now+600,rules['id'],rules['config']))
  for u in (a,b):self.call('/scheduling/availability',{'game':'efootball','tz':'UTC','weekly':{str(i):[{'start':'00:00','end':'23:59'}] for i in range(7)},'unavailable':False},u['token'])
  return a,b,c,mid,now
 def proposal(self,u,mid,at):return self.call('/scheduling/propose',{'kind':'open','match':mid,'at':at},u['token'])
 def decide(self,u,mid,r,action='accept'):return self.call('/scheduling/'+action,{'kind':'open','match':mid,'request':r['request']},u['token'])
 def test_availability_validation_timezone_and_preservation(self):
  a,b,c,mid,now=self.setup_match()
  with self.server.db() as d:d.execute('UPDATE gb_game_ids SET availability=? WHERE uid=? AND game=?',(json.dumps([{'start':now+10,'end':now+900}]),a['id'],'efootball'))
  self.call('/scheduling/availability',{'game':'efootball','tz':'Africa/Lagos','weekly':{'0':[{'start':'19:00','end':'23:00'}]},'unavailable':True},a['token'])
  x=self.call('/scheduling/availability?game=efootball',token=a['token']);self.assertTrue(x['unavailable']);self.assertEqual(x['tz'],'Africa/Lagos');self.assertEqual(len(x['dated_windows']),1)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/queue',{'game':'efootball'},a['token'])
  for bad in [{'0':[{'start':'22:00','end':'22:00'}]},{'0':[{'start':'19:00','end':'23:00'},{'start':'20:00','end':'21:00'}]}]:
   with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/availability',{'game':'efootball','weekly':bad},a['token'])
  self.assertEqual(ms.wall_time('2026-10-20T20:00','Africa/Lagos'),ms.wall_time('2026-10-20T19:00','UTC'))
  for t in ['2026-03-08T02:30','2026-11-01T01:30']:
   with self.assertRaises(ValueError):ms.wall_time(t,'America/New_York')
 def test_mutual_decisions_and_stale_requests(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+7200)
  with self.assertRaises(urllib.error.HTTPError):self.decide(a,mid,r)
  with self.assertRaises(urllib.error.HTTPError):self.decide(c,mid,r)
  self.decide(b,mid,r)
  r2=self.proposal(a,mid,now+10800)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT scheduled FROM gb_open_schedule WHERE fixture=?',(mid,)).fetchone()[0],now+7200)
  self.decide(b,mid,r2,'decline')
  with self.server.db() as d:self.assertEqual(d.execute('SELECT scheduled FROM gb_open_schedule WHERE fixture=?',(mid,)).fetchone()[0],now+7200)
  with self.assertRaises(urllib.error.HTTPError):self.decide(b,mid,r2)
  r3=self.proposal(a,mid,now+10800);self.decide(a,mid,r3,'withdraw')
  r4=self.proposal(a,mid,now+10800);self.decide(b,mid,r4)
  with self.assertRaises(urllib.error.HTTPError):self.proposal(a,mid,now+14400)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_rank_history').fetchone()[0],0)
 def test_three_reminders_reschedule_invalidation_and_idempotency(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+7200);self.decide(b,mid,r)
  for lead in ms.OFFSETS:ms.tick(self.server,now+7200-lead)
  with self.server.db() as d:
   self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_match_reminders WHERE state='queued'").fetchone()[0],6)
   count=d.execute('SELECT COUNT(*) FROM gb_notices').fetchone()[0]
  ms.tick(self.server,now+7200)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_notices').fetchone()[0],count)
  # Fresh setup avoids pretending a result already checked in can be rescheduled.
  with patch('match_scheduling.time.time',return_value=now+60):
   r=self.proposal(a,mid,now+10800);self.decide(b,mid,r)
  with self.server.db() as d:
   old=list(d.execute("SELECT n.* FROM gb_notices n JOIN gb_notice_links l ON l.notice=n.id WHERE l.purpose='reminder' AND l.version=1"));self.assertTrue(all(not ms.valid_notice(d,x,now+61) for x in old));self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_match_reminders WHERE version=2 AND state='pending'").fetchone()[0],6)
 def test_late_schedule_cancel_restart_and_delivery_target(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+600);self.decide(b,mid,r)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_match_reminders').fetchone()[0],2)
  ms.init(self.server);ms.init(self.server)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_match_reminders').fetchone()[0],2);d.execute("UPDATE gb_matches SET state='cancelled' WHERE id=?",(mid,))
  ms.tick(self.server,now+600)
  with self.server.db() as d:self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_match_reminders WHERE state='suppressed'").fetchone()[0],2)
  with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/admin',token=b['token'])
 def test_duplicate_conflict_expiry_and_availability_recheck(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+7200);self.assertEqual(r,self.proposal(a,mid,now+7200))
  with self.assertRaises(urllib.error.HTTPError):self.proposal(b,mid,now+7500)
  self.call('/scheduling/availability',{'game':'efootball','unavailable':True},b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.decide(b,mid,r)
  ms.tick(self.server,now+601)
  with self.server.db() as d:self.assertEqual(d.execute('SELECT state FROM gb_schedule_requests').fetchone()[0],'expired');self.assertIsNone(d.execute('SELECT scheduled FROM gb_open_schedule').fetchone()[0])

 def test_fixture_request_cutoff_and_restart_preserve_jobs(self):
  a,b,c,mid,now=self.setup_match()
  lid=self.call('/gaming/create',{'name':'Schedule fixture','game':'efootball'},a['token'])['id']
  fid=__import__('uuid').uuid4().hex
  with self.server.db() as d:d.execute("INSERT INTO fixtures(id,league,round,a,b,opens,due) VALUES(?,?,1,?,?,?,?)",(fid,lid,a['id'],b['id'],now-60,now+86400))
  req=self.call('/scheduling/propose',{'kind':'fixture','match':fid,'at':now+7200},a['token'])
  self.call('/scheduling/accept',{'kind':'fixture','match':fid,'request':req['request']},b['token'])
  ms.init(self.server)
  with self.server.db() as d:self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_match_reminders WHERE kind='fixture'").fetchone()[0],6)
  with patch('match_scheduling.time.time',return_value=now+7000):
   with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/propose',{'kind':'fixture','match':fid,'at':now+10800},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/propose',{'kind':'fixture','match':fid,'at':now+90000},a['token'])
 def test_old_request_notice_does_not_revive_and_notice_is_private(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+7200)
  with self.server.db() as d:nid=d.execute("SELECT notice FROM gb_notice_links WHERE purpose='request'").fetchone()[0]
  n=self.call('/scheduling/notice?id='+str(nid),token=b['token']);self.assertEqual(n['match_id'],mid);self.assertEqual(n['kind'],'open')
  with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/notice?id='+str(nid),token=c['token'])
  self.decide(b,mid,r,'decline');self.proposal(a,mid,now+7500)
  with self.assertRaises(urllib.error.HTTPError):self.call('/scheduling/notice?id='+str(nid),token=b['token'])
 def test_idle_server_generates_reminders_without_client_requests(self):
  a,b,c,mid,now=self.setup_match();r=self.proposal(a,mid,now+1803);self.decide(b,mid,r)
  deadline=time.monotonic()+6;count=0
  while time.monotonic()<deadline:
   with self.server.db() as d:count=d.execute("SELECT COUNT(*) FROM gb_notice_links WHERE purpose='reminder'").fetchone()[0]
   if count:break
   time.sleep(.2)
  self.assertEqual(count,2)
 def test_overnight_windows_and_opponent_overlap(self):
  a,b,c,mid,now=self.setup_match()
  sample=ms.wall_time('2026-10-20T00:30','UTC')
  self.call('/scheduling/availability',{'game':'efootball','tz':'UTC','weekly':{'0':[{'start':'23:00','end':'01:00'}]}},a['token'])
  self.call('/scheduling/availability',{'game':'efootball','tz':'Africa/Lagos','weekly':{'1':[{'start':'01:00','end':'03:00'}]}},b['token'])
  with self.server.db() as d:self.assertTrue(ms.available(d,a['id'],'efootball',sample));self.assertTrue(ms.available(d,b['id'],'efootball',sample));self.assertIsNotNone(ms.overlap(d,a['id'],b['id'],'efootball',sample,sample+3600))
 def test_legacy_proposal_migration_and_missed_reminder_suppression(self):
  a,b,c,mid,now=self.setup_match()
  with self.server.db() as d:d.execute('INSERT INTO gb_open_schedule(fixture,proposer,proposed) VALUES(?,?,?)',(mid,a['id'],now-60))
  ms.init(self.server);ms.init(self.server)
  with self.server.db() as d:
   self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_schedule_requests').fetchone()[0],1)
   self.assertEqual(d.execute('SELECT state FROM gb_schedule_requests').fetchone()[0],'expired')
  r=self.proposal(a,mid,now+7200);self.decide(b,mid,r)
  ms.tick(self.server,now+7200-1800+61)
  with self.server.db() as d:
   self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_match_reminders WHERE lead=1800 AND state='suppressed'").fetchone()[0],2)
   self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_notice_links WHERE purpose='reminder'").fetchone()[0],0)
