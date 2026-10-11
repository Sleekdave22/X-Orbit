package com.guardianlab.chat

import android.app.*
import android.content.Intent
import android.os.*
import java.util.concurrent.Executors

class MessageAlerts:Service(){
 private val handler=Handler(Looper.getMainLooper());private val worker=Executors.newSingleThreadExecutor();private var busy=false
 private val prefs by lazy {getSharedPreferences("account",MODE_PRIVATE)}
 private val poll=object:Runnable {override fun run(){if(!busy){busy=true;worker.execute {try{val api=ChatApi(prefs.getString("server","")!!,prefs.getString("token","")!!);val inbox=api.request("/inbox").getJSONArray("ids");if(inbox.length()>0)api.request("/delivered",org.json.JSONObject().put("ids",inbox));val users=api.request("/users").getJSONArray("users");val primed=prefs.getBoolean("alertsPrimed",false);for(i in 0 until users.length()){val u=users.getJSONObject(i);val id=u.getString("id");val latest=u.optLong("latest");val old=prefs.getLong("alert-$id",0);if(u.optInt("unread")==0)getSystemService(NotificationManager::class.java).cancel(id.hashCode());if(primed&&latest>old&&u.optInt("unread")>0&&!prefs.getBoolean("foreground",false)){val tap=PendingIntent.getActivity(this@MessageAlerts,id.hashCode(),Intent(this@MessageAlerts,MainActivity::class.java).putExtra("peer",id).putExtra("peerName",u.getString("name")),PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE);val n=Notification.Builder(this@MessageAlerts,"messages").setSmallIcon(android.R.drawable.ic_dialog_email).setContentTitle("GuardianChat").setContentText("New message from ${u.getString("name")}").setNumber(u.optInt("unread")).setContentIntent(tap).setAutoCancel(true).build();getSystemService(NotificationManager::class.java).notify(id.hashCode(),n)};prefs.edit().putLong("alert-$id",latest).apply()};prefs.edit().putBoolean("alertsPrimed",true).apply()}catch(_:Exception){}finally{busy=false}}};handler.postDelayed(this,5000)}}
 override fun onCreate(){super.onCreate();val manager=getSystemService(NotificationManager::class.java);manager.createNotificationChannel(NotificationChannel("connection","Wi-Fi notification connection",NotificationManager.IMPORTANCE_LOW));manager.createNotificationChannel(NotificationChannel("messages","New messages",NotificationManager.IMPORTANCE_HIGH));val tap=PendingIntent.getActivity(this,0,Intent(this,MainActivity::class.java),PendingIntent.FLAG_IMMUTABLE);startForeground(7,Notification.Builder(this,"connection").setSmallIcon(android.R.drawable.ic_dialog_email).setContentTitle("GuardianChat notifications active").setContentText("Listening for messages on your Mac’s Wi-Fi server").setContentIntent(tap).setOngoing(true).build());handler.post(poll)}
 override fun onStartCommand(intent:Intent?,flags:Int,startId:Int)=START_NOT_STICKY
 override fun onBind(intent:Intent?)=null
 override fun onTimeout(startId:Int,fgsType:Int){stopSelf()}
 override fun onDestroy(){handler.removeCallbacksAndMessages(null);worker.shutdown();super.onDestroy()}
}
