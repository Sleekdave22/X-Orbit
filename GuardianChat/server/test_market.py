import unittest,urllib.error
import test_server
class MarketTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 def shop(self,name,shop):
  u=self.register(name);self.call('/market/register',{'shop_name':shop,'about':'About '+shop},u['token']);return u
 def ad(self,u,title,**kw):
  body={'title':title,'category':'Gaming','description':'','price':''};body.update(kw);return self.call('/market/post_ad',body,u['token'])['id']
 def test_shop_required_before_posting_and_names_unique(self):
  a=self.register('Ada')
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/post_ad',{'title':'Boots','category':'Fashion'},a['token'])
  self.call('/market/register',{'shop_name':'Ada Boots'},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/register',{'shop_name':'Other'},a['token'])
  b=self.register('Bayo')
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/register',{'shop_name':'ada boots'},b['token'])
 def test_every_ad_visible_to_everyone_and_search_returns_accounts(self):
  a=self.shop('Ada','Ada Boots');b=self.shop('Bayo','Bayo Games');c=self.register('Chi')
  self.ad(a,'Leather boots',category='Fashion',price='N15,000');self.ad(a,'Canvas boots',category='Fashion');self.ad(b,'FC Mobile coins',description='fast top-up')
  allads=self.call('/market/ads',token=c['token'])
  self.assertEqual({x['title'] for x in allads['ads']},{'Leather boots','Canvas boots','FC Mobile coins'})
  r=self.call('/market/ads?q=boots',token=c['token']);self.assertEqual(r['mode'],'accounts')
  self.assertEqual([s['shop_name'] for s in r['accounts']],['Ada Boots']);self.assertEqual(r['accounts'][0]['matches'],2)
  r=self.call('/market/ads?q=top-up',token=c['token']);self.assertEqual([s['shop_name'] for s in r['accounts']],['Bayo Games'])
  r=self.call('/market/ads?q=bayo',token=c['token']);self.assertEqual(len(r['accounts']),1)
  self.assertEqual(self.call('/market/ads?q=zzz',token=c['token'])['accounts'],[])
  self.assertEqual(self.call('/market/ads?q=%25',token=c['token'])['accounts'],[])
 def test_limits_expiry_removal_and_reports(self):
  a=self.shop('Ada','Ada Boots');us=[self.register('R'+str(i)) for i in range(3)]
  ids=[self.ad(a,'Item '+str(i)) for i in range(5)]
  with self.assertRaises(urllib.error.HTTPError):self.ad(a,'Sixth in an hour')
  with self.server.db() as d:d.execute("UPDATE market_ads SET expires=1 WHERE id=?",(ids[0],))
  titles=[x['title'] for x in self.call('/market/ads',token=us[0]['token'])['ads']];self.assertNotIn('Item 0',titles)
  self.call('/market/remove_ad',{'id':ids[1]},a['token']);self.assertNotIn('Item 1',[x['title'] for x in self.call('/market/ads',token=us[0]['token'])['ads']])
  for u in us:self.call('/market/report',{'id':ids[2],'reason':'spam'},u['token'])
  self.assertNotIn('Item 2',[x['title'] for x in self.call('/market/ads',token=us[0]['token'])['ads']])
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/admin_restore',{'id':ids[2]},us[0]['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/report',{'id':ids[3]},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/remove_ad',{'id':ids[3]},us[0]['token'])
 def test_admin_restores_held_ad(self):
  a=self.shop('Ada','Ada Boots');us=[self.register('R'+str(i)) for i in range(3)];i=self.ad(a,'Boots')
  for u in us:self.call('/market/report',{'id':i},u['token'])
  with self.server.db() as d:d.execute('INSERT OR IGNORE INTO game_admin VALUES(?)',(us[0]['id'],))
  self.assertEqual(len(self.call('/market/summary',token=us[0]['token'])['held']),1)
  self.call('/market/admin_restore',{'id':i},us[0]['token'])
  self.assertIn('Boots',[x['title'] for x in self.call('/market/ads',token=us[1]['token'])['ads']])
 def test_unauthenticated_rejected(self):
  with self.assertRaises(urllib.error.HTTPError):self.call('/market/ads')
if __name__=='__main__':unittest.main()
