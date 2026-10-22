import unittest
import urllib.error
import test_server

class PreferencesTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 def test_isolation_validation_and_repeated_save(self):
  a,b=self.register('A'),self.register('B')
  with self.assertRaises(urllib.error.HTTPError):self.call('/preferences')
  for _ in range(2):self.assertEqual(self.call('/preferences',{'palette':'ocean'},a['token'])['palette'],'ocean')
  self.assertEqual(self.call('/preferences',token=a['token'])['palette'],'ocean');self.assertEqual(self.call('/preferences',token=b['token'])['palette'],'oxblood-gold')
  for body in ({'palette':'invalid'},{'palette':'rose','uid':b['id']},{'palette':'#ff0000'},{}):
   with self.assertRaises(urllib.error.HTTPError):self.call('/preferences',body,a['token'])
  self.assertEqual(self.call('/preferences',token=a['token'])['palette'],'ocean')
  with self.server.db() as db:self.assertEqual(db.execute('SELECT COUNT(*) FROM account_preferences').fetchone()[0],1)
 def test_all_presets_have_readable_text(self):
  a=self.register('A');choices=self.call('/preferences',token=a['token'])['choices']
  def luminance(hex):
   rgb=[int(hex[i:i+2],16)/255 for i in (1,3,5)];return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip((.2126,.7152,.0722),rgb))
  def contrast(a,b):
   a,b=sorted((luminance(a),luminance(b)));return (b+.05)/(a+.05)
  for p in choices:
   self.assertGreaterEqual(contrast(p['bubble'],p['ink']),4.5,p['id']);self.assertGreaterEqual(contrast(p['accent'],'#ffffff'),4.5,p['id'])
