package com.guardianlab.chat
import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.FirebaseOptions
import com.google.firebase.messaging.FirebaseMessaging
import org.json.JSONObject
object PushRegistration {
 fun ready(context:Context):Boolean {return try {if(FirebaseApp.getApps(context).none {it.name==FirebaseApp.DEFAULT_APP_NAME}){val data=JSONObject(context.assets.open("firebase-config.json").bufferedReader().use {it.readText()});val project=data.getJSONObject("project_info");val clients=data.getJSONArray("client");var client:JSONObject?=null;for(i in 0 until clients.length()){val candidate=clients.getJSONObject(i);if(candidate.getJSONObject("client_info").getJSONObject("android_client_info").getString("package_name")==context.packageName)client=candidate};val c=client?:return false;FirebaseApp.initializeApp(context,FirebaseOptions.Builder().setApplicationId(c.getJSONObject("client_info").getString("mobilesdk_app_id")).setApiKey(c.getJSONArray("api_key").getJSONObject(0).getString("current_key")).setGcmSenderId(project.getString("project_number")).setProjectId(project.getString("project_id")).build())};true}catch(_:Exception){false}}
 fun sync(context:Context,newToken:String?=null){if(!ready(context))return;val prefs=context.getSharedPreferences("account",Context.MODE_PRIVATE);val session=prefs.getString("token","")?:"";val base=prefs.getString("server","")?:"";if(session.isEmpty()||base.isEmpty())return
fun send(token:String){Thread {try{if(prefs.getString("token","")!=session)return@Thread;ChatApi(base,session).request(if(prefs.getBoolean("incomingCalls",true))"/push/register"else "/push/unregister",JSONObject().put("push_token",token))}catch(_:Exception){}}.start()}
if(newToken!=null)send(newToken)else FirebaseMessaging.getInstance().token.addOnSuccessListener {send(it)}}
}
