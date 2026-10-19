import unittest,sqlite3,json
import gamebox_core as g
CFG=dict(g.DEFAULT)
def db():
 d=sqlite3.connect(':memory:');d.row_factory=sqlite3.Row
 d.executescript("CREATE TABLE gb_ratings(uid TEXT,game TEXT,rating REAL DEFAULT 1000,played INTEGER DEFAULT 0,activity INTEGER DEFAULT 0,PRIMARY KEY(uid,game));CREATE TABLE gb_rating_tx(id INTEGER PRIMARY KEY AUTOINCREMENT,ref TEXT,uid TEXT,game TEXT,before REAL,change REAL,after REAL,k INTEGER,expected REAL,opponent TEXT,opponent_rating REAL,outcome REAL,formula INTEGER DEFAULT 1,created INTEGER,UNIQUE(ref,uid));CREATE TRIGGER nu BEFORE UPDATE ON gb_rating_tx BEGIN SELECT RAISE(ABORT,'Rating history is immutable'); END;CREATE TRIGGER nd BEFORE DELETE ON gb_rating_tx BEGIN SELECT RAISE(ABORT,'Rating history is immutable'); END;")
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
unittest.main() if __name__=='__main__' else None
