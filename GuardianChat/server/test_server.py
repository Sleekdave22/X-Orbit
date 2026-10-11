import unittest, threading, tempfile, urllib.request, urllib.error, json, base64
from server import ChatServer
from pathlib import Path
class ChatTest(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.server=ChatServer(('127.0.0.1',0),self.tmp.name)
  self.thread=threading.Thread(target=self.server.serve_forever,daemon=True);self.thread.start()
  self.base=f'http://127.0.0.1:{self.server.server_port}'
 def tearDown(self):self.server.shutdown();self.server.server_close();self.tmp.cleanup()
 def call(self,path,body=None,token=''):
  request=urllib.request.Request(self.base+path,data=json.dumps(body).encode() if body is not None else None,headers={'Authorization':'Bearer '+token,'Content-Type':'application/json'})
  with urllib.request.urlopen(request,timeout=5) as r:
   data=r.read();return json.loads(data) if r.headers.get_content_type()=='application/json' else data
 def register(self,name):
  user=self.call('/register',{'invite':self.server.invite,'name':name})
  # Existing transfer tests use explicitly paired test accounts.
  for other in getattr(self,'accounts',[]):self.call('/contacts',{'code':other['id']},user['token'])
  self.accounts=getattr(self,'accounts',[])+[user]
  return user
 def test_password_change_requires_current_password(self):
  a=self.register('Password account')
  self.call('/password',{'password':'first passphrase 123'},a['token'])
  for old in ['', 'wrong password']:
   with self.assertRaises(urllib.error.HTTPError):self.call('/password',{'password':'second passphrase 456','current_password':old},a['token'])
  self.call('/password',{'password':'second passphrase 456','current_password':'first passphrase 123'},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/login',{'identity':a['id'],'password':'first passphrase 123'})
  self.assertEqual(self.call('/login',{'identity':a['id'],'password':'second passphrase 456'})['id'],a['id'])
 def test_account_login_keeps_data_and_revokes_only_logged_out_session(self):
  a=self.register('Account A');b=self.register('Account B')
  mid=self.call('/messages',{'peer':b['id'],'text':'Account-owned history','client_id':'history'},a['token'])['id']
  with self.assertRaises(urllib.error.HTTPError):self.call('/logout',{},a['token'])
  self.call('/password',{'password':'test passphrase 123'},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/password',{'password':'overwrite password'},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/login',{'identity':a['id'],'password':'incorrect'})
  signed=self.call('/login',{'identity':a['nickname'],'password':'test passphrase 123'})
  self.assertEqual(signed['id'],a['id'])
  self.assertEqual(self.call('/messages?peer='+b['id']+'&after=0',token=signed['token'])['messages'][0]['id'],mid)
  self.call('/logout',{},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/users',token=a['token'])
  self.assertEqual(self.call('/users',token=signed['token'])['users'][0]['id'],b['id'])
  c=self.call('/register',{'invite':self.server.invite,'name':'Account C'});self.assertEqual(self.call('/users',token=c['token'])['users'],[])
 def test_video_above_old_limit(self):
  a=self.register('Video sender');b=self.register('Video recipient')
  payload=base64.b64encode(b'v'*(8*1024*1024+1)).decode()
  body={'peer':b['id'],'client_id':'large-video','filename':'clip.mp4','mime':'video/mp4','data':payload}
  result=self.call('/messages',body,a['token']);self.assertGreater(result['id'],0)
  body.update(client_id='large-image',filename='image.jpg',mime='image/jpeg')
  with self.assertRaises(urllib.error.HTTPError) as e:self.call('/messages',body,a['token'])
  self.assertEqual(e.exception.code,413)
 def test_private_contacts_and_required_pairing(self):
  a=self.call('/register',{'invite':self.server.invite,'name':'A'})
  b=self.call('/register',{'invite':self.server.invite,'name':'B'})
  c=self.call('/register',{'invite':self.server.invite,'name':'C'})
  self.assertEqual(self.call('/users',token=a['token'])['users'],[])
  with self.assertRaises(urllib.error.HTTPError) as e:self.call('/messages',{'peer':b['id'],'text':'blocked','client_id':'before'},a['token'])
  self.assertEqual(e.exception.code,403)
  for code in [a['id'],'unknown']:
   with self.assertRaises(urllib.error.HTTPError):self.call('/contacts',{'code':code},a['token'])
  self.call('/contacts',{'code':b['id'].upper()},a['token'])
  self.call('/contacts',{'code':b['id']},a['token'])
  self.assertEqual([u['id'] for u in self.call('/users',token=a['token'])['users']],[b['id']])
  self.assertEqual([u['id'] for u in self.call('/users',token=b['token'])['users']],[a['id']])
  self.assertEqual(self.call('/users',token=c['token'])['users'],[])
  self.call('/messages',{'peer':b['id'],'text':'allowed','client_id':'after'},a['token'])
 def test_real_transfer_and_access_boundaries(self):
  a,b,c=[self.register(n) for n in ['David','Test friend','Third account']]
  payload={'peer':b['id'],'text':'Test message','client_id':'unique-1','filename':'../../note.txt','mime':'text/plain','data':base64.b64encode(b'test attachment').decode()}
  sent=self.call('/messages',payload,a['token']);retry=self.call('/messages',payload,a['token']);self.assertEqual(sent,retry)
  received=self.call('/messages?peer='+a['id'],token=b['token'])['messages'];self.assertEqual(len(received),1);self.assertEqual(received[0]['filename'],'note.txt')
  fid=received[0]['fileid'];self.assertEqual(self.call('/files/'+fid,token=b['token']),b'test attachment')
  saved=self.server.file_path(fid,'note.txt','text/plain')
  self.assertTrue(saved.is_file());self.assertEqual(saved.suffix,'.txt');self.assertEqual(saved.read_bytes(),b'test attachment')
  legacy=Path(self.tmp.name)/'files'/fid;saved.rename(legacy)
  self.server.migrate_files();self.assertTrue(saved.exists());self.assertFalse(legacy.exists())
  self.assertEqual(self.call('/files/'+fid,token=b['token']),b'test attachment')
  with self.assertRaises(urllib.error.HTTPError) as error:self.call('/files/'+fid,token=c['token'])
  self.assertEqual(error.exception.code,404)
  self.assertEqual(self.call('/messages?peer='+a['id'],token=c['token'])['messages'],[])
  with self.assertRaises(urllib.error.HTTPError) as error:self.call('/users')
  self.assertEqual(error.exception.code,401)
 def test_unread_counts_and_scoped_read(self):
  a,b,c=[self.register(n) for n in ['A','B','C']]
  first=self.call('/messages',{'peer':b['id'],'text':'one','client_id':'one'},a['token'])
  second=self.call('/messages',{'peer':b['id'],'text':'two','client_id':'two'},a['token'])
  users=self.call('/users',token=b['token'])['users'];self.assertEqual(next(u for u in users if u['id']==a['id'])['unread'],2)
  self.call('/read',{'peer':a['id'],'through':second['id']},c['token'])
  self.call('/read',{'peer':a['id'],'through':first['id']},b['token'])
  users=self.call('/users',token=b['token'])['users'];self.assertEqual(next(u for u in users if u['id']==a['id'])['unread'],1)
  self.call('/read',{'peer':a['id'],'through':second['id']},b['token'])
  users=self.call('/users',token=b['token'])['users'];self.assertEqual(next(u for u in users if u['id']==a['id'])['unread'],0)
 def test_delivery_and_read_receipts_belong_to_recipient(self):
  a,b,c=[self.register(n) for n in ['A','B','C']]
  sent=self.call('/messages',{'peer':b['id'],'text':'receipt','client_id':'receipt'},a['token'])
  def receipt():return self.call('/receipts?peer='+b['id'],token=a['token'])['receipts'][0]
  self.assertEqual(receipt()['delivered_at'],0);self.assertEqual(receipt()['read_at'],0)
  self.assertEqual(self.call('/inbox',token=b['token'])['ids'],[sent['id']])
  self.call('/delivered',{'ids':[sent['id']]},c['token']);self.assertEqual(receipt()['delivered_at'],0)
  self.call('/delivered',{'ids':[sent['id']]},b['token']);self.assertGreater(receipt()['delivered_at'],0);self.assertEqual(receipt()['read_at'],0)
  self.call('/read',{'peer':a['id'],'through':sent['id']},b['token']);self.assertGreater(receipt()['read_at'],0)
  self.assertEqual(self.call('/receipts?peer='+b['id'],token=c['token'])['receipts'],[])
 def test_legacy_messages_do_not_become_new_unread(self):
  import sqlite3
  with tempfile.TemporaryDirectory() as folder:
   with sqlite3.connect(Path(folder)/'chat.sqlite') as db:
    db.execute('CREATE TABLE messages(id INTEGER PRIMARY KEY AUTOINCREMENT,sender TEXT,recipient TEXT,text TEXT,filename TEXT,mime TEXT,fileid TEXT,size INTEGER,time INTEGER,client_id TEXT,UNIQUE(sender,client_id))')
    db.execute("INSERT INTO messages(sender,recipient,text,time,client_id) VALUES('a','b','old',1,'legacy')")
   migrated=ChatServer(('127.0.0.1',0),folder)
   try:
    with migrated.db() as db:self.assertGreater(db.execute('SELECT read_at FROM messages').fetchone()[0],0)
   finally:migrated.server_close()
 def test_profiles_nicknames_and_private_contact_card(self):
  a=self.call('/register',{'invite':self.server.invite,'name':'Alice','nickname':'Alice_Test'})
  b=self.call('/register',{'invite':self.server.invite,'name':'Bob','nickname':'bob_test'})
  self.assertEqual(a['nickname'],'alice_test')
  with self.assertRaises(urllib.error.HTTPError) as e:self.call('/register',{'invite':self.server.invite,'name':'Duplicate','nickname':'ALICE_TEST'})
  self.assertEqual(e.exception.code,409)
  with self.assertRaises(urllib.error.HTTPError):self.call('/profile?id='+a['id'],token=b['token'])
  self.call('/contacts',{'code':'@ALICE_TEST'},b['token'])
  card=self.call('/profile?id='+a['id'],token=b['token']);self.assertEqual(card['id'],a['id']);self.assertNotIn('token_hash',card)
  changed=self.call('/profile',{'nickname':'new_alice','name':'Alice Updated'},a['token']);self.assertEqual(changed['id'],a['id'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/profile',{'nickname':'BOB_TEST'},a['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/profile',{'avatar':base64.b64encode(b'<svg/>').decode(),'avatar_mime':'image/svg+xml'},a['token'])
  self.assertEqual(self.call('/profile',token=a['token'])['nickname'],'new_alice')
 def test_filename_extension_and_safety(self):
  path=self.server.file_path('123','../../photo','image/jpeg')
  self.assertEqual(path.name,'photo__123.jpg');self.assertEqual(path.parent,Path(self.tmp.name)/'files')
  self.assertEqual(self.server.file_path('456','photo','image/jpeg').name,'photo__456.jpg')
 def test_bad_invite_and_bad_recipient(self):
  with self.assertRaises(urllib.error.HTTPError):self.call('/register',{'invite':'wrong','name':'Nobody'})
  a=self.register('David')
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages',{'peer':'missing','text':'hello','client_id':'1'},a['token'])
 def test_oversized_file_and_invalid_base64(self):
  a,b=self.register('David'),self.register('Friend')
  for data in ['not valid base64!',base64.b64encode(b'x'*(8*1024*1024+1)).decode()]:
   with self.assertRaises(urllib.error.HTTPError):self.call('/messages',{'peer':b['id'],'client_id':'large','data':data},a['token'])
 def test_view_once_access_and_no_second_open(self):
  a,b,c=[self.register(n) for n in ['Sender','Recipient','Other']]
  sent=self.call('/messages',{'peer':b['id'],'text':'secret test text','client_id':'once1','view_once':True,'filename':'private.txt','mime':'text/plain','data':base64.b64encode(b'private test bytes').decode()},a['token'])
  listing=self.call('/messages?peer='+a['id'],token=b['token'])['messages'][0]
  self.assertEqual(listing['text'],'');self.assertIsNone(listing['fileid']);self.assertEqual(listing['view_once'],1)
  with self.server.db() as db:fid=db.execute('SELECT fileid FROM messages WHERE id=?',(sent['id'],)).fetchone()['fileid']
  with self.assertRaises(urllib.error.HTTPError):self.call('/files/'+fid,token=b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/open',{'message_id':sent['id']},c['token'])
  opened=self.call('/open',{'message_id':sent['id']},b['token']);self.assertEqual(opened['text'],'secret test text')
  req=urllib.request.Request(self.base+'/files/'+fid,headers={'Authorization':'Bearer '+b['token'],'X-View-Token':opened['view_token']})
  with urllib.request.urlopen(req) as r:self.assertEqual(r.read(),b'private test bytes')
  with self.assertRaises(urllib.error.HTTPError) as error:self.call('/open',{'message_id':sent['id']},b['token'])
  self.assertEqual(error.exception.code,409)
  self.call('/close',{'message_id':sent['id']},b['token'])
  with self.server.db() as db:
   cleared=db.execute('SELECT * FROM messages WHERE id=?',(sent['id'],)).fetchone()
  self.assertEqual(cleared['text'],'');self.assertIsNone(cleared['fileid']);self.assertIsNone(cleared['filename'])
  self.assertFalse(self.server.file_path(fid,'private.txt','text/plain').exists())
  self.assertEqual(self.call('/messages?peer='+b['id'],token=a['token'])['messages'][0]['text'],'')
  with self.assertRaises(urllib.error.HTTPError):urllib.request.urlopen(req)
  self.assertEqual(self.call('/messages?peer='+a['id'],token=b['token'])['messages'][0]['opened'],1)
 def test_expired_view_deletes_content(self):
  a,b=self.register('Sender'),self.register('Recipient')
  sent=self.call('/messages',{'peer':b['id'],'text':'expiry test','client_id':'expiry','view_once':True,'filename':'photo.jpg','mime':'image/jpeg','data':base64.b64encode(b'image bytes').decode()},a['token'])
  opened=self.call('/open',{'message_id':sent['id']},b['token'])
  path=self.server.file_path(opened['fileid'],'photo.jpg','image/jpeg')
  with self.server.db() as db:db.execute('UPDATE messages SET lease_until=0 WHERE id=?',(sent['id'],))
  self.server.expire_views();self.assertFalse(path.exists())
  with self.server.db() as db:row=db.execute('SELECT * FROM messages WHERE id=?',(sent['id'],)).fetchone()
  self.assertEqual(row['text'],'');self.assertIsNone(row['fileid'])
 def test_view_once_text_and_unsupported_file(self):
  a,b=self.register('Sender'),self.register('Recipient')
  sent=self.call('/messages',{'peer':b['id'],'text':'text-only private test','client_id':'once-text','view_once':True},a['token'])
  self.assertEqual(self.call('/open',{'message_id':sent['id']},b['token'])['text'],'text-only private test')
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages',{'peer':b['id'],'client_id':'once-file','view_once':True,'mime':'application/zip','data':base64.b64encode(b'zip').decode()},a['token'])
if __name__=='__main__':unittest.main()
