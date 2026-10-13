import unittest,urllib.error
from collections import Counter
import test_server
from server import account_qr
class GamingTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 def league(self):
  us=[self.register('Player'+str(n)) for n in range(9)]
  for u in us:self.call('/gaming/profile',{'tag':u['name'],'game_id':'player-'+u['id'],'adult':True,'feature':True,'handle':'@'+u['name']},u['token'])
  l=self.call('/gaming/create',{'name':'Test division','game':'efootball'},us[0]['token'])['id']
  for u in us[:8]:self.call('/gaming/join',{'league':l},u['token'])
  self.call('/gaming/moderator',{'league':l,'identity':us[8]['id']},us[0]['token']);self.call('/gaming/start',{'league':l},us[0]['token']);return us,l
 def view(self,l,u):return self.call('/gaming/summary?league='+l,token=u['token'])
 def result(self,f,us,l):
  users={u['id']:u for u in us};self.call('/gaming/report',{'league':l,'fixture':f['id'],'score_a':3,'score_b':1,'image':account_qr(f['id'])},users[f['a']]['token']);self.call('/gaming/confirm',{'league':l,'fixture':f['id']},users[f['b']]['token'])
 def test_scheduler_and_capacity(self):
  us,l=self.league();fs=self.view(l,us[0])['fixtures'];self.assertEqual(len(fs),28);self.assertEqual(len({tuple(sorted((f['a'],f['b']))) for f in fs}),28);self.assertEqual(set(Counter(p for f in fs for p in (f['a'],f['b'])).values()),{7})
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/join',{'league':l},us[8]['token'])
 def test_pending_permissions_and_confirmation(self):
  us,l=self.league();f=self.view(l,us[0])['fixtures'][0];users={u['id']:u for u in us};self.call('/gaming/report',{'league':l,'fixture':f['id'],'score_a':3,'score_b':1,'image':account_qr(f['id'])},users[f['a']]['token']);self.assertTrue(all(r['points']==0 for r in self.view(l,us[0])['table']))
  stranger=next(u for u in us[:8] if u['id'] not in (f['a'],f['b'],us[0]['id']))
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/evidence?fixture='+f['id']+'&player='+f['a'],token=stranger['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/confirm',{'league':l,'fixture':f['id']},stranger['token'])
  self.call('/gaming/confirm',{'league':l,'fixture':f['id']},users[f['b']]['token']);self.assertEqual(self.view(l,us[0])['table'][0]['points'],3)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/confirm',{'league':l,'fixture':f['id']},users[f['b']]['token'])
 def test_dispute_review(self):
  us,l=self.league();f=self.view(l,us[0])['fixtures'][0];users={u['id']:u for u in us};self.call('/gaming/report',{'league':l,'fixture':f['id'],'score_a':3,'score_b':1,'image':account_qr(f['id'])},users[f['a']]['token']);self.call('/gaming/dispute',{'league':l,'fixture':f['id'],'reason':'Wrong score shown'},users[f['b']]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/confirm',{'league':l,'fixture':f['id']},users[f['b']]['token'])
  self.call('/gaming/review',{'league':l,'fixture':f['id'],'score_a':2,'score_b':1,'reason':'Checked screenshot and both players'},us[8]['token']);self.assertEqual(self.view(l,us[0])['fixtures'][0]['state'],'confirmed')
 def test_complete_final_and_consent(self):
  us,l=self.league()
  with self.server.db() as d:d.execute('UPDATE fixtures SET opens=0 WHERE league=?',(l,))
  for f in self.view(l,us[0])['fixtures']:self.result(f,us,l)
  self.call('/gaming/finals',{'league':l},us[0]['token'])
  for f in [f for f in self.view(l,us[0])['fixtures'] if f['stage']=='semi']:self.result(f,us,l)
  final=next(f for f in self.view(l,us[0])['fixtures'] if f['stage']=='final');self.result(final,us,l);state=self.view(l,us[0]);self.assertEqual(state['league']['state'],'finished');self.assertEqual(len(state['champions']),1);u=next(u for u in us if u['id']==state['league']['champion']);self.call('/gaming/profile',{'tag':u['name'],'game_id':'gamer','adult':True,'feature':False},u['token']);self.assertEqual(self.view(l,u)['champions'],[])
 def test_age_auth_and_sponsor_url(self):
  a=self.register('Adult')
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/profile',{'tag':'gamer','game_id':'id','adult':False},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/summary')
  us,l=self.league()
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/sponsor',{'league':l,'sponsor':'Brand','url':'javascript:alert(1)'},us[0]['token'])
 def test_reward_requires_funding_and_freezes_after_start(self):
  a=self.register('Organiser');self.call('/gaming/profile',{'tag':'organiser','game_id':'gamer','adult':True},a['token']);l=self.call('/gaming/create',{'name':'Reward test','game':'efootball'},a['token'])['id']
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/sponsor',{'league':l,'reward':'10000 NGN','funded':False},a['token'])
  self.call('/gaming/sponsor',{'league':l,'reward':'10000 NGN','funded':True},a['token'])
  with self.server.db() as d:d.execute("UPDATE leagues SET state='active' WHERE id=?",(l,))
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/sponsor',{'league':l,'reward':'No prize','funded':True},a['token'])
 def test_duplicate_screenshot_is_rejected(self):
  us,l=self.league();fs=self.view(l,us[0])['fixtures'][:2];users={u['id']:u for u in us};proof=account_qr('same-proof')
  self.call('/gaming/report',{'league':l,'fixture':fs[0]['id'],'score_a':2,'score_b':1,'image':proof},users[fs[0]['a']]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/report',{'league':l,'fixture':fs[1]['id'],'score_a':2,'score_b':1,'image':proof},users[fs[1]['a']]['token'])
 def test_organiser_cannot_approve_own_match(self):
  us,l=self.league();f=next(f for f in self.view(l,us[0])['fixtures'][:4] if us[0]['id'] in (f['a'],f['b']));users={u['id']:u for u in us};self.call('/gaming/report',{'league':l,'fixture':f['id'],'score_a':2,'score_b':1,'image':account_qr(f['id'])},users[f['a']]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/review',{'league':l,'fixture':f['id'],'score_a':2,'score_b':1,'reason':'I approve myself'},us[0]['token'])
 def test_static_gaming_page_does_not_require_bearer(self):
  page=self.call('/gaming.html');self.assertIn(b'Gamebox',page)
 def test_snapshot_game_ids_survive_profile_changes(self):
  us,l=self.league();u=us[1];original='player-'+u['id'];self.call('/gaming/profile',{'tag':'Changed','game_id':'new-id','adult':True},u['token']);f=next(f for f in self.view(l,u)['fixtures'] if u['id'] in (f['a'],f['b']));self.assertEqual(f['game_ids'][u['id']],original)

 def test_cup_slots_and_automatic_advancement(self):
  us=[self.register('Cup'+str(n)) for n in range(8)]
  for u in us:self.call('/gaming/profile',{'tag':u['name'],'game_id':'cup-'+u['id'],'adult':True},u['token'])
  l=self.call('/gaming/create',{'name':'Cup test','game':'efootball','format':'cup'},us[0]['token'])['id']
  for n,u in enumerate(us,1):self.assertEqual(self.call('/gaming/join',{'league':l},u['token'])['slot'],n)
  self.assertEqual(self.call('/gaming/join',{'league':l},us[0]['token'])['slot'],1)
  self.assertEqual(len(self.view(l,us[0])['slots']),8)
  self.call('/gaming/start',{'league':l},us[0]['token'])
  q=self.view(l,us[0])['fixtures'];self.assertEqual(len(q),4);self.assertEqual((q[0]['a'],q[0]['b']),(us[0]['id'],us[1]['id']))
  for f in q:self.result(f,us,l)
  semis=[f for f in self.view(l,us[0])['fixtures'] if f['stage']=='semi'];self.assertEqual(len(semis),2)
  for f in semis:self.result(f,us,l)
  final=[f for f in self.view(l,us[0])['fixtures'] if f['stage']=='final'];self.assertEqual(len(final),1);self.result(final[0],us,l)
  summary=self.view(l,us[0]);self.assertEqual(summary['league']['champion'],us[0]['id']);self.assertEqual(summary['league']['state'],'finished')

 def test_match_room_comments_and_closed_room(self):
  us,l=self.league();f=self.view(l,us[0])['fixtures'][0]
  self.call('/gaming/comment',{'league':l,'fixture':f['id'],'text':'Good luck!'},us[8]['token'])
  r=self.call('/gaming/room?fixture='+f['id'],token=us[0]['token']);self.assertEqual(r['comments'][0]['text'],'Good luck!');self.assertTrue(r['active'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/room?fixture='+f['id'])
  self.result(f,us,l)
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/comment',{'league':l,'fixture':f['id'],'text':'Late comment'},us[8]['token'])
 def test_weekly_sponsor_art_and_profile_picture_consent(self):
  us,l=self.league();avatar=account_qr('rank-picture')
  self.call('/profile',{'name':us[0]['name'],'nickname':'player0','avatar':avatar,'avatar_mime':'image/png'},us[0]['token'])
  table=self.view(l,us[1])['table'];self.assertEqual(next(r for r in table if r['uid']==us[0]['id'])['avatar'],avatar)
  self.call('/gaming/profile',{'tag':us[0]['name'],'game_id':'player-'+us[0]['id'],'adult':True,'feature':False},us[0]['token'])
  self.assertEqual(next(r for r in self.view(l,us[1])['table'] if r['uid']==us[0]['id'])['avatar'],'')
  self.assertEqual(next(r for r in self.view(l,us[0])['table'] if r['uid']==us[0]['id'])['avatar'],avatar)
  self.call('/gaming/sponsor',{'league':l,'sponsor':'GuardianLab','week':'2026-W42','art':avatar},us[0]['token'])
  league=self.view(l,us[0])['league'];self.assertEqual(league['sponsor_week'],'2026-W42');self.assertTrue(league['sponsor_art'].startswith('data:image/png;base64,'))
 def test_admin_scoping_and_comment_audit(self):
  us,l=self.league();f=self.view(l,us[0])['fixtures'][0]
  self.assertEqual(self.call('/gaming/admin',token=us[1]['token'])['competitions'],[])
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/admin?league='+l,token=us[1]['token'])
  self.call('/gaming/comment',{'league':l,'fixture':f['id'],'text':'Test moderation'},us[1]['token'])
  admin=self.call('/gaming/admin?league='+l,token=us[8]['token']);cid=admin['comments'][0]['id']
  with self.assertRaises(urllib.error.HTTPError):self.call('/gaming/hide_comment',{'league':l,'comment':cid,'reason':'Test reason'},us[1]['token'])
  self.call('/gaming/hide_comment',{'league':l,'comment':cid,'reason':'Test reason'},us[8]['token'])
  self.assertEqual(self.call('/gaming/room?fixture='+f['id'],token=us[1]['token'])['comments'],[])
  audit=self.call('/gaming/admin?league='+l,token=us[0]['token']);self.assertTrue(audit['comments'][0]['hidden']);self.assertIn('comment_hidden',[r['action'] for r in audit['audit']])
if __name__=='__main__':unittest.main()
