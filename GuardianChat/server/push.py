"""Optional call-only FCM transport. Credential material never goes to the Android app."""
from pathlib import Path
from datetime import timedelta
class PushGateway:
 def __init__(self,path):
  self.enabled=False;self.app=None
  if not Path(path).is_file():return
  try:
   import firebase_admin
   from firebase_admin import credentials
   self.app=firebase_admin.initialize_app(credentials.Certificate(str(path)),name='guardianchat-push');self.enabled=True
  except Exception:pass
 def send(self,token,data):
  if not self.enabled:return
  from firebase_admin import messaging
  messaging.send(messaging.Message(token=token,data=data,android=messaging.AndroidConfig(priority='high',ttl=timedelta(seconds=600 if data.get('event')=='gamebox_notice' else 45))),app=self.app)
