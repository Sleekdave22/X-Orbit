"""Appearance migration must not rewrite custom themes or competition controls."""
import copy
import json
import unittest
import gamebox_core
import test_server

class ThemeMigrationTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp
 tearDown=test_server.ChatTest.tearDown

 def install(self, theme):
  config=copy.deepcopy(gamebox_core.DEFAULT)
  config['theme']=theme
  config['accept_seconds']=180
  config['announcement']='Keep this announcement'
  with self.server.db() as d:
   d.execute('INSERT INTO gb_versions(config,actor,reason,created) VALUES(?,?,?,0)',(json.dumps(config),'owner','Before theme migration'))
  return config

 def read(self):
  with self.server.db() as d:
   record=d.execute('SELECT id,config FROM gb_versions ORDER BY id DESC LIMIT 1').fetchone()
   return record['id'],json.loads(record['config'])

 def test_default_only_and_idempotent(self):
  original=self.install(dict(gamebox_core.LEGACY_DEFAULT_THEME))
  gamebox_core.init(self.server)
  version,current=self.read()
  self.assertEqual(current,dict(original,theme=gamebox_core.DEFAULT['theme']))
  self.assertEqual(set(current['theme']),set(gamebox_core.LEGACY_DEFAULT_THEME))
  gamebox_core.init(self.server)
  self.assertEqual(self.read()[0],version)

 def test_custom_theme_is_preserved(self):
  for changed in ({'accent':'#123456'},{'radius':10}):
   custom=dict(gamebox_core.LEGACY_DEFAULT_THEME,**changed)
   original=self.install(custom)
   version,_=self.read()
   gamebox_core.init(self.server)
   self.assertEqual(self.read(),(version,original))
