package com.guardianlab.chat

import android.Manifest
import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.net.Uri
import android.os.Build

/** Fetch previews over authenticated HTTPS, never from untrusted push text. */
object MessageNotifications {
 fun receive(context:Context,data:Map<String,String>){
  val prefs=context.getSharedPreferences("account",Context.MODE_PRIVATE)
  val owner=prefs.getString("id","")?:return
  if(data["recipient"]!=owner||!prefs.getBoolean("notifications",true))return
  val id=data["message_id"]?.toLongOrNull()?.takeIf {it>0}?:return
  if((data["expires_at"]?.toLongOrNull()?:0)<=System.currentTimeMillis()/1000)return
  if(Build.VERSION.SDK_INT>=33&&context.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED)return
  // Foreground polling owns in-app banners. Avoid duplicate alerts for the same message.
  if(MainActivity.appVisible)return
  val token=prefs.getString("token","")?.takeIf {it.isNotEmpty()}?:return
  try {
   val m=ChatApi(prefs.getString("server","")!!,token).request("/messages/notification?id=$id",timeoutMillis=4500)
   if(prefs.getString("id","")!=owner||prefs.getString("token","")!=token||!prefs.getBoolean("notifications",true)||MainActivity.appVisible)return
   val state=context.getSharedPreferences("message_push_$owner",Context.MODE_PRIVATE)
   synchronized(this){
    if(state.getLong("latest-${m.getString("peer")}",0)>=id)return
    val manager=context.getSystemService(NotificationManager::class.java)
    manager.createNotificationChannel(NotificationChannel("chat_messages_v2","Chat messages",NotificationManager.IMPORTANCE_HIGH).apply {enableVibration(true)})
    if(!manager.areNotificationsEnabled())return
    val open=Intent(context,MainActivity::class.java).setData(Uri.parse("xorbit://message/$owner/$id"))
     .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP or Intent.FLAG_ACTIVITY_SINGLE_TOP)
     .putExtra("notificationAccount",owner).putExtra("peer",m.getString("peer")).putExtra("peerName",m.getString("name")).putExtra("messageId",id)
    val tap=PendingIntent.getActivity(context,0,open,PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    val body=m.getString("preview")
    manager.notify(m.getString("peer").hashCode(),Notification.Builder(context,"chat_messages_v2")
     .setSmallIcon(android.R.drawable.ic_dialog_email).setContentTitle(m.getString("name")).setContentText(body)
     .setStyle(Notification.BigTextStyle().bigText(body)).setCategory(Notification.CATEGORY_MESSAGE)
     .setVisibility(Notification.VISIBILITY_PRIVATE).setContentIntent(tap).setAutoCancel(true).setOnlyAlertOnce(false).build())
    state.edit().putLong("latest-${m.getString("peer")}",id).apply()
   }
  }catch(error:Exception){android.util.Log.w("XOrbitMessagePush","Message notification unavailable: "+error.javaClass.simpleName)}
 }
}
