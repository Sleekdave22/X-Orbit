import base64
import threading
import time
import unittest
import urllib.error
import test_server

class MessageNotificationTest(unittest.TestCase):
 setUp=test_server.ChatTest.setUp;tearDown=test_server.ChatTest.tearDown;call=test_server.ChatTest.call;register=test_server.ChatTest.register
 def send(self,a,b,text='Hello',client='message',**kw):
  return self.call('/messages',dict(peer=b['id'],text=text,client_id=client,**kw),a['token'])['id']
 def test_preview_recipient_only_hidden_protected_and_no_read_side_effect(self):
  a,b,c=self.register('Sender'),self.register('Recipient'),self.register('Other')
  for i,kw in enumerate([{},dict(view_once=True),dict(protected_media=True,data=base64.b64encode(b'picture').decode(),filename='private.jpg',mime='image/jpeg')]):
   mid=self.send(a,b,'Secret text',str(i),**kw)
   preview=self.call('/messages/notification?id='+str(mid),token=b['token'])
   self.assertEqual(preview['preview'],['Secret text','View-once content','Protected media'][i]);self.assertEqual(preview['peer'],a['id'])
   self.assertEqual(set(preview),{'id','peer','name','preview','time'})
   for account in (a,c):
    with self.assertRaises(urllib.error.HTTPError):self.call('/messages/notification?id='+str(mid),token=account['token'])
   with self.server.db() as db:self.assertEqual(db.execute('SELECT read_at FROM messages WHERE id=?',(mid,)).fetchone()[0],0)
  self.call('/messages/delete',dict(message_id=mid,scope='me'),b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages/notification?id='+str(mid),token=b['token'])
 def test_push_after_commit_metadata_only_duplicate_send_and_forward(self):
  a,b=self.register('Sender'),self.register('Recipient');device='test-message-device-'+'a'*40
  self.call('/push/register',dict(push_token=device),b['token'])
  class Push:
   enabled=True
   def __init__(self):self.events=[];self.ready=threading.Event()
   def send(self,token,data):self.events.append((token,data));self.ready.set()
  push=Push();self.server.push=push
  mid=self.send(a,b,'Preview stays off FCM');self.assertTrue(push.ready.wait(2))
  self.assertEqual(push.events[0][0],device);event=push.events[0][1]
  self.assertEqual(set(event),{'event','recipient','message_id','expires_at'});self.assertEqual(event['event'],'chat_message');self.assertEqual(event['message_id'],str(mid))
  self.assertEqual(self.call('/messages/notification?id='+str(mid),token=b['token'])['preview'],'Preview stays off FCM')
  self.assertEqual(self.send(a,b,'Preview stays off FCM'),mid);time.sleep(.05);self.assertEqual(len(push.events),1)
  push.ready.clear();forward=self.call('/messages/forward',dict(message_id=mid,peer=b['id'],client_id='forward'),a['token'])['id']
  self.assertTrue(push.ready.wait(2));self.assertEqual(push.events[-1][1]['message_id'],str(forward))
 def test_read_deleted_blocked_and_logged_out_do_not_expose_preview(self):
  a,b=self.register('Sender'),self.register('Recipient');mid=self.send(a,b)
  self.call('/read',dict(peer=a['id'],through=mid),b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages/notification?id='+str(mid),token=b['token'])
  mid=self.send(a,b,client='next');self.call('/social/block',dict(target=a['id']),b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages/notification?id='+str(mid),token=b['token'])
  self.call('/password',{'password':'notification-test-password'},b['token']);self.call('/logout',{},b['token'])
  with self.assertRaises(urllib.error.HTTPError):self.call('/messages/notification?id='+str(mid),token=b['token'])
