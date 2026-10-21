package com.guardianlab.chat

import android.app.*
import android.content.Intent
import android.content.pm.ServiceInfo
import android.media.projection.MediaProjection
import android.os.*
import org.json.JSONObject
import org.webrtc.*
import java.util.UUID
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Video-only, consent-gated screen sharing. No camera, microphone or local recording. */
class GameplayBroadcastService : Service() {
 companion object {
  @Volatile var room=""; private set
  @Volatile var status="Screen broadcast is off"; private set
  @Volatile var active=false; private set
  const val STOP="com.guardianlab.chat.STOP_GAMEPLAY"
 }
 private val worker=Executors.newSingleThreadScheduledExecutor()
 private var factory:PeerConnectionFactory?=null
 private var egl:EglBase?=null
 private var helper:SurfaceTextureHelper?=null
 @Volatile private var capturer:ScreenCapturerAndroid?=null
 private var source:VideoSource?=null
 private var track:VideoTrack?=null
 private var api:ChatApi?=null
 private var cursor=0L
 @Volatile private var closed=false
 private val screenOff=object:android.content.BroadcastReceiver(){override fun onReceive(context:android.content.Context?,intent:Intent?){if(intent?.action==Intent.ACTION_SCREEN_OFF)stopSelf()}}
 private var receiverRegistered=false
 private fun enqueue(work:()->Unit){if(closed||worker.isShutdown)return;try{worker.execute {if(!closed)work()}}catch(_:java.util.concurrent.RejectedExecutionException){}}
 private var begun=false
 private var failures=0
 private var peer:PeerConnection?=null
 private var relayPeer=""
 private val relayClient=UUID.randomUUID().toString()
 private var offerSent=false
 override fun onBind(intent:Intent?)=null
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int):Int {
  if(intent?.action==STOP){stopSelf();return START_NOT_STICKY}
  if(intent==null||active||room.isNotEmpty()){stopSelf();return START_NOT_STICKY}
  val rid=intent.getStringExtra("room")?:""
  if(!rid.matches(Regex("[a-f0-9]{32}"))){stopSelf();return START_NOT_STICKY}
  val consent=if(Build.VERSION.SDK_INT>=33)intent.getParcelableExtra("consent",Intent::class.java) else @Suppress("DEPRECATION") intent.getParcelableExtra<Intent>("consent")
  if(consent==null){stopSelf();return START_NOT_STICKY}
  val prefs=getSharedPreferences("account",MODE_PRIVATE)
  try {api=ChatApi(prefs.getString("server","")!!,prefs.getString("token","")!!)}catch(_:Exception){stopSelf();return START_NOT_STICKY}
  room=rid;status="Starting screen broadcast…"
  val manager=getSystemService(NotificationManager::class.java)
  manager.createNotificationChannel(NotificationChannel("gameplay_live","Gameplay screen sharing",NotificationManager.IMPORTANCE_LOW))
  val stop=PendingIntent.getService(this,0,Intent(this,javaClass).setAction(STOP),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
  val open=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java).putExtra("gameboxNotice",true),PendingIntent.FLAG_IMMUTABLE or PendingIntent.FLAG_UPDATE_CURRENT)
  val notice=Notification.Builder(this,"gameplay_live").setSmallIcon(android.R.drawable.presence_video_online).setContentTitle("OrbitPlay · sharing your screen").setContentText("Video only · tap Stop to end broadcasting").setContentIntent(open).setOngoing(true).addAction(Notification.Action.Builder(null,"Stop",stop).build()).build()
  try {startForeground(880030,notice,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)}catch(_:Exception){status="Screen-sharing service could not start";room="";stopSelf();return START_NOT_STICKY}
   if(Build.VERSION.SDK_INT>=33)registerReceiver(screenOff,android.content.IntentFilter(Intent.ACTION_SCREEN_OFF),RECEIVER_NOT_EXPORTED)else registerReceiver(screenOff,android.content.IntentFilter(Intent.ACTION_SCREEN_OFF));receiverRegistered=true
  enqueue {try {
   PeerConnectionFactory.initialize(PeerConnectionFactory.InitializationOptions.builder(applicationContext).createInitializationOptions())
   egl=EglBase.create();factory=PeerConnectionFactory.builder().setVideoEncoderFactory(DefaultVideoEncoderFactory(egl!!.eglBaseContext,true,true)).setVideoDecoderFactory(DefaultVideoDecoderFactory(egl!!.eglBaseContext)).createPeerConnectionFactory()
   helper=SurfaceTextureHelper.create("OrbitGameplayCapture",egl!!.eglBaseContext)
   source=factory!!.createVideoSource(true)
   capturer=ScreenCapturerAndroid(consent,object:MediaProjection.Callback(){override fun onStop(){status="Screen sharing stopped";stopSelf()}})
   capturer!!.initialize(helper,applicationContext,source!!.capturerObserver)
   val size=captureSize();source!!.adaptOutputFormat(size.first,size.second,15)
   if(closed)return@enqueue
   capturer!!.startCapture(size.first,size.second,15)
   if(closed){capturer!!.stopCapture();return@enqueue}
   track=factory!!.createVideoTrack("orbit-gameplay",source)
   request("stream_begin");begun=true;if(closed)return@enqueue;active=true;status="Connecting screen broadcast…"
   offer()
   worker.scheduleWithFixedDelay({poll()},0,1500,TimeUnit.MILLISECONDS)
  }catch(_:Exception){status="Could not start screen broadcast";stopSelf()}}
  return START_NOT_STICKY
 }
 private fun request(action:String,body:JSONObject=JSONObject()):JSONObject {body.put("room",room);return api!!.request("/gaming/$action",body,6000)}
 private fun observer(success:(SessionDescription?)->Unit)=object:SdpObserver {
  override fun onCreateSuccess(s:SessionDescription?){enqueue {if(!closed)success(s)}}
  override fun onSetSuccess(){enqueue {if(!closed)success(null)}}
  override fun onCreateFailure(error:String?){enqueue {dropAll("Could not negotiate screen stream")}}
  override fun onSetFailure(error:String?){enqueue {dropAll("Could not negotiate screen stream")}}
 }
 private fun dropAll(message:String){status=message;stopSelf()}
 private fun offer(){
  if(closed||!active||track==null)return
  if(peer!=null)return
  val config=PeerConnection.RTCConfiguration(emptyList());config.sdpSemantics=PeerConnection.SdpSemantics.UNIFIED_PLAN
  val pc=factory!!.createPeerConnection(config,object:PeerConnection.Observer {
   override fun onSignalingChange(state:PeerConnection.SignalingState?){}
   override fun onIceConnectionChange(state:PeerConnection.IceConnectionState?){enqueue {when(state){
    PeerConnection.IceConnectionState.CONNECTED,PeerConnection.IceConnectionState.COMPLETED->status="LIVE · screen video only. Open your game."
    PeerConnection.IceConnectionState.FAILED->dropAll("Screen broadcast stopped: connection lost")
    else->{}
   }}}
   override fun onIceConnectionReceivingChange(receiving:Boolean){}
   override fun onIceGatheringChange(state:PeerConnection.IceGatheringState?){if(state==PeerConnection.IceGatheringState.COMPLETE)enqueue {sendOffer()}}
   override fun onIceCandidate(c:IceCandidate?){}
   override fun onIceCandidatesRemoved(c:Array<out IceCandidate>?){}
   override fun onAddStream(s:MediaStream?){}
   override fun onRemoveStream(s:MediaStream?){}
   override fun onDataChannel(channel:DataChannel?){}
   override fun onRenegotiationNeeded(){}
   override fun onAddTrack(receiver:RtpReceiver?,streams:Array<out MediaStream>?){}
  })?:throw IllegalStateException("No peer connection")
  peer=pc
  val sender=pc.addTrack(track,listOf("orbit-gameplay"));val parameters=sender.parameters
  parameters.encodings.forEach {it.maxBitrateBps=600000;it.maxFramerate=15};sender.parameters=parameters
  pc.createOffer(observer {s->if(s!=null&&peer===pc)pc.setLocalDescription(observer {
   if(pc.iceGatheringState()==PeerConnection.IceGatheringState.COMPLETE)sendOffer()
   else worker.schedule({enqueue {if(!offerSent)dropAll("Screen connection setup timed out. Try again.")}},15,TimeUnit.SECONDS)
  },s)},MediaConstraints())
 }
 private fun sendOffer(){
  val pc=peer?:return
  val description=pc.localDescription?:return
  if(pc.iceGatheringState()!=PeerConnection.IceGatheringState.COMPLETE)return
  if(offerSent||closed)return
  offerSent=true
  try {
   val answer=api!!.request("/gaming/stream_relay_offer",JSONObject().put("room",room).put("role","publish").put("client_id",relayClient).put("type","offer").put("sdp",description.description),20000)
   relayPeer=answer.getString("peer_id")
   if(closed)return
   pc.setRemoteDescription(observer {},SessionDescription(SessionDescription.Type.ANSWER,answer.getString("sdp")))
  }catch(_:Exception){dropAll("Screen stream could not connect. Reopen the room to try again.")}
 }
 private fun poll(){if(closed||!active)return;try {
  val r=api!!.request("/gaming/stream-signals?room=$room&after=$cursor",timeoutMillis=6000)
  if(!r.getJSONObject("live").optBoolean("active")){status="Live session ended";stopSelf();return}
  // Heartbeat and room lifetime only. Spectators connect to the server relay;
  // their arrival never creates another phone upload / encoder.
  val signals=r.getJSONArray("signals")
  for(i in 0 until signals.length())cursor=maxOf(cursor,signals.getJSONObject(i).getLong("id"))
  failures=0
 }catch(_:Exception){failures++;if(failures>=4){status="Screen broadcast stopped: connection lost";stopSelf()}}}
 private fun captureSize():Pair<Int,Int>{val metrics=resources.displayMetrics;val scale=minOf(1.0,960.0/maxOf(metrics.widthPixels,metrics.heightPixels));return Pair(maxOf(2,(metrics.widthPixels*scale).toInt()/2*2),maxOf(2,(metrics.heightPixels*scale).toInt()/2*2))}
 override fun onConfigurationChanged(config:android.content.res.Configuration){super.onConfigurationChanged(config);enqueue {if(active){val size=captureSize();source?.adaptOutputFormat(size.first,size.second,15);capturer?.changeCaptureFormat(size.first,size.second,15)}}}
 override fun onTaskRemoved(rootIntent:Intent?){stopSelf()}
 override fun onDestroy(){active=false;closed=true
  // Stop capture immediately, even if a signaling request is still in flight.
  try{capturer?.stopCapture()}catch(_:Exception){}
  if(receiverRegistered){unregisterReceiver(screenOff);receiverRegistered=false};worker.execute {
  if(relayPeer.isNotEmpty())try{request("stream_relay_close",JSONObject().put("peer_id",relayPeer))}catch(_:Exception){}
  if(begun)try{request("stream_end")}catch(_:Exception){}
  peer?.let {it.close();it.dispose()};peer=null;relayPeer=""
  try{capturer?.dispose()}catch(_:Exception){}
  track?.dispose();source?.dispose();helper?.dispose();factory?.dispose();egl?.release()
  room="";status="Screen broadcast ended";worker.shutdown()
 };stopForeground(STOP_FOREGROUND_REMOVE);super.onDestroy()}
}
