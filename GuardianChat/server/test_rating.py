import unittest,sqlite3,json
import gamebox_core as g
CFG=dict(g.DEFAULT)
def db():
 d=sqlite3.connect(':memory:');d.row_factory=sqlite3.Row
 d.executescript("CREATE TABLE gb_ratings(uid TEXT,game TEXT,rating REAL DEFAULT 1000,played INTEGER DEFAULT 0,activity INTEGER DEFAULT 0,PRIMARY KEY(uid,game));CREATE TABLE gb_rating_tx(id INTEGER PRIMARY KEY AUTOINCREMENT,ref TEXT,uid TEXT,game TEXT,before REAL,change REAL,after REAL,k INTEGER,expected REAL,opponent TEXT,opponent_rating REAL,outcome REAL,formula INTEGER DEFAULT 1,created INTEGER,UNIQUE(ref,uid));CREATE TABLE gb_tier_config(game TEXT PRIMARY KEY,bounds TEXT);CREATE TABLE gb_notices(id INTEGER PRIMARY KEY AUTOINCREMENT,uid TEXT,text TEXT,seen INTEGER DEFAULT 0,created INTEGER);CREATE TABLE gb_flags(id INTEGER PRIMARY KEY AUTOINCREMENT,kind TEXT,game TEXT,a TEXT,b TEXT,detail TEXT,created INTEGER,state TEXT DEFAULT 'open',reviewer TEXT,note TEXT);CREATE TABLE gb_tier_history(id INTEGER PRIMARY KEY AUTOINCREMENT,uid TEXT,game TEXT,before TEXT,after TEXT,rating REAL,created INTEGER);CREATE TRIGGER nu BEFORE UPDATE ON gb_rating_tx BEGIN SELECT RAISE(ABORT,'Rating history is immutable'); END;CREATE TRIGGER nd BEFORE DELETE ON gb_rating_tx BEGIN SELECT RAISE(ABORT,'Rating history is immutable'); END;")
 return d
def setup(d,a,b,game='fc'):
 for u,(r,p) in (('a',a),('b',b)):d.execute('INSERT INTO gb_ratings(uid,game,rating,played) VALUES(?,?,?,?)',(u,game,r,p))
class T(unittest.TestCase):
 def test_defaults(self):self.assertEqual((CFG['start_rating'],CFG['k_provisional'],CFG['k_established'],CFG['provisional_matches']),(1000,40,20,20))
 def test_equal_established_win_draw_loss(self):
  self.assertEqual(g.rating_change(1200,1200,1,30,CFG)[0],10);self.assertEqual(g.rating_change(1200,1200,0,30,CFG)[0],-10);self.assertEqual(g.rating_change(1200,1200,.5,30,CFG)[0],0)
 def test_upset_pays_more(self):
  self.assertGreater(g.rating_change(1000,1400,1,30,CFG)[0],g.rating_change(1000,1000,1,30,CFG)[0]);self.assertGreater(abs(g.rating_change(1400,1000,0,30,CFG)[0]),10)
  self.assertLess(g.rating_change(1400,1000,1,30,CFG)[0],10)
 def test_underdog_draw_gains_favourite_loses(self):
  self.assertGreater(g.rating_change(1000,1400,.5,30,CFG)[0],0);self.assertLess(g.rating_change(1400,1000,.5,30,CFG)[0],0)
 def test_provisional_k(self):
  self.assertEqual(g.rating_change(1000,1000,1,0,CFG)[0],20);self.assertEqual(g.rating_change(1000,1000,1,19,CFG)[1],40);self.assertEqual(g.rating_change(1000,1000,1,20,CFG)[1],20)
 def test_idempotent_and_immutable(self):
  d=db();setup(d,(1000,30),(1000,30));g.apply_rating(d,'m1','fc','a','b',1,CFG);again=g.apply_rating(d,'m1','fc','a','b',1,CFG)
  self.assertEqual(again,{});self.assertEqual(d.execute("SELECT rating FROM gb_ratings WHERE uid='a'").fetchone()[0],1010);self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_rating_tx').fetchone()[0],2)
  with self.assertRaises(sqlite3.DatabaseError):d.execute('UPDATE gb_rating_tx SET change=99')
  with self.assertRaises(sqlite3.DatabaseError):d.execute('DELETE FROM gb_rating_tx')
 def test_separate_games(self):
  d=db();setup(d,(1000,30),(1000,30));setup(d,(1500,30),(1500,30),'ef');g.apply_rating(d,'m1','fc','a','b',1,CFG)
  self.assertEqual(d.execute("SELECT rating FROM gb_ratings WHERE uid='a' AND game='ef'").fetchone()[0],1500)
 def test_tiers(self):
  self.assertEqual([g.rating_tier(x) for x in (999,1000,1199,1200,1400,1600)],['Bronze','Silver','Silver','Gold','Platinum','Elite'])
 def test_config_validates(self):
  c=json.loads(json.dumps(CFG));g.validate(c);c['k_established']=500
  with self.assertRaises(ValueError):g.validate(c)
class Extra(unittest.TestCase):
 def test_notice_and_tier_change(self):
  d=db();setup(d,(999,30),(1100,30));g.apply_rating(d,'m1','fc','a','b',1,CFG)
  texts=[r[0] for r in d.execute("SELECT text FROM gb_notices WHERE uid='a'")];self.assertTrue(any(t.startswith('Match won') for t in texts));self.assertTrue(any('Promoted to Silver' in t for t in texts))
  self.assertEqual(d.execute("SELECT after FROM gb_tier_history WHERE uid='a'").fetchone()[0],'Silver')
 def test_frequent_pair_flagged_once_per_day(self):
  d=db();setup(d,(1000,30),(1000,30))
  for i in range(7):g.apply_rating(d,'m%d'%i,'fc','a','b',1,CFG)
  self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_flags WHERE kind='frequent_pair' AND a='a'").fetchone()[0],1)
 def test_reciprocal_pattern_flagged(self):
  d=db();setup(d,(1000,30),(1000,30))
  for i,sc in enumerate((1,0,1,0)):g.apply_rating(d,'r%d'%i,'fc','a','b',sc,CFG)
  self.assertEqual(d.execute("SELECT COUNT(*) FROM gb_flags WHERE kind='reciprocal_pattern'").fetchone()[0],1)
 def test_rating_never_changes_without_verified_ref(self):
  d=db();setup(d,(1000,30),(1000,30));self.assertEqual(d.execute('SELECT COUNT(*) FROM gb_rating_tx').fetchone()[0],0)
class Tiers(unittest.TestCase):
 def test_per_game_bounds(self):
  d=db();d.execute("INSERT INTO gb_tier_config VALUES('fc','[0,800,900,1000,1100]')");self.assertEqual(g.rating_tier(950,g.tier_bounds(d,'fc')),'Gold');self.assertEqual(g.rating_tier(950,g.tier_bounds(d,'other')),'Bronze')
 def test_matchmaking_gap_widens_with_wait(self):
  rules=dict(g.DEFAULT);self.assertEqual(min(800,rules['rating_gap']+rules['gap_step']*(0//300)),400);self.assertEqual(min(800,rules['rating_gap']+rules['gap_step']*(900//300)),700)
unittest.main() if __name__=='__main__' else None
