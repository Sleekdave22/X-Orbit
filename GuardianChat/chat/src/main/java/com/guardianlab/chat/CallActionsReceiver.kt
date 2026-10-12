package com.guardianlab.chat

import android.app.NotificationManager
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import org.json.JSONObject

class CallActionsReceiver:BroadcastReceiver(){
 override fun onReceive(context:Context,intent:Intent){val id=intent.getStringExtra("callId")?:return;if(!id.matches(Regex("[a-f0-9]{32}")))return;val prefs=context.getSharedPreferences("account",Context.MODE_PRIVATE);prefs.edit().putString("declinedCall",id).apply();context.getSystemService(NotificationManager::class.java).cancel(880001);val result=goAsync();Thread {try{val base=prefs.getString("server","")!!;val token=prefs.getString("token","")!!;if(token.isNotEmpty())ChatApi(base,token).request("/calls/end",JSONObject().put("id",id))}catch(_:Exception){}finally{result.finish()}}.start()}
}
