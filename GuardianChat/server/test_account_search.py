import unittest, urllib.error, urllib.parse
import test_social

class AccountSearchTest(unittest.TestCase):
 setUp=test_social.SocialTest.setUp;tearDown=test_social.SocialTest.tearDown;call=test_social.SocialTest.call;reg=test_social.SocialTest.reg;act=test_social.SocialTest.act
 def search(self,user,query,offset=0):
  return self.call('/social/search?'+urllib.parse.urlencode({'q':query,'offset':offset}),token=user['token'])
 def test_privacy_exact_identifiers_blocks_and_no_contact_grant(self):
  a,b,c=self.reg('Searcher'),self.reg('Discover Player'),self.reg('Discover Private')
  self.act(b,'settings',discoverable=True);self.act(c,'settings',private=True,discoverable=True)
  self.assertEqual([u['id'] for u in self.search(a,'discover')['users']],[b['id']])
  self.assertEqual([u['id'] for u in self.search(a,c['id'])['users']],[c['id']])
  self.assertEqual(self.call('/users',token=a['token'])['users'],[])
  self.assertEqual(set(self.search(a,c['id'])['users'][0]),{'id','name','nickname','avatar','avatar_mime','contact'})
  self.act(c,'block',target=a['id']);self.assertEqual(self.search(a,c['id'])['users'],[])
  self.act(a,'block',target=b['id']);self.assertEqual(self.search(a,'discover')['users'],[])
 def test_boundaries_auth_and_literal_queries(self):
  a,b=self.reg('Searcher'),self.reg('Player 100%_winner')
  self.act(b,'settings',discoverable=True)
  self.assertEqual(len(self.search(a,'%_')['users']),1)
  self.assertEqual(self.search(a,'__')['users'],[])
  with self.assertRaises(urllib.error.HTTPError):self.call('/social/search?q=Player')
  for query,offset in [('a',0),('x'*61,0),('Player',-1),('Player',10001)]:
   with self.assertRaises(urllib.error.HTTPError):self.search(a,query,offset)
 def test_pagination_stable_and_case_insensitive_exact_nickname(self):
  a=self.reg('Searcher')
  for i in range(23):
   b=self.reg('Team player '+str(i).zfill(2));self.act(b,'settings',discoverable=True)
  first=self.search(a,'Team');second=self.search(a,'Team',first['next_offset'])
  self.assertEqual(len(first['users']),20);self.assertEqual(len(second['users']),3);self.assertIsNone(second['next_offset'])
  self.assertEqual(len({u['id'] for u in first['users']+second['users']}),23)
  self.assertEqual(self.search(a,'@'+b['nickname'].upper())['users'][0]['id'],b['id'])
