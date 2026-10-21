import json,time,unittest,urllib.error
import test_server,test_gamebox_core
class SeasonAvailabilityTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register;players=test_gamebox_core.CoreTest.players
 def test_weekly_only_registration_snapshot_legacy_and_unavailable(self):
  a,b,c=self.players();now=int(time.time());season=self.call('/gamebox/season_create',{'name':'Weekly availability','game':'efootball','tier':0,'opens':now,'closes':now+120},a['token'])['id']
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/season_register',{'season':season},a['token'])
  weekly={'0':[{'start':'19:00','end':'23:00'}]};self.call('/scheduling/availability',{'game':'efootball','tz':'Africa/Lagos','weekly':weekly},a['token'])
  self.call('/gamebox/season_register',{'season':season},a['token']);self.call('/gamebox/season_register',{'season':season},a['token'])
  with self.server.db() as d:
   saved=json.loads(d.execute('SELECT snapshot FROM gb_season_availability WHERE season=? AND uid=?',(season,a['id'])).fetchone()[0]);self.assertEqual(saved['weekly'],weekly);self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_season_entries WHERE season=? AND uid=?',(season,a['id'])).fetchone()[0],1)
  self.call('/scheduling/availability',{'game':'efootball','weekly':{'1':[{'start':'20:00','end':'22:00'}]}},a['token'])
  with self.server.db() as d:self.assertEqual(json.loads(d.execute('SELECT snapshot FROM gb_season_availability WHERE uid=?',(a['id'],)).fetchone()[0])['weekly'],weekly)
  self.call('/scheduling/availability',{'game':'efootball','unavailable':True},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gamebox/season_register',{'season':season},a['token'])
  self.call('/gamebox/identity',{'game':'efootball','game_id':'game-'+b['id'],'region':'Nigeria','tz':'UTC','availability':[{'start':now+100,'end':now+3600}]},b['token']);self.call('/gamebox/season_register',{'season':season},b['token'])
  self.call('/gamebox/season_leave',{'season':season},a['token'])
  with self.server.db() as d:self.assertFalse(d.execute('SELECT 1 FROM gb_season_availability WHERE uid=?',(a['id'],)).fetchone());self.assertEqual(d.execute('SELECT COUNT(*) FROM fin_journals').fetchone()[0],0)
