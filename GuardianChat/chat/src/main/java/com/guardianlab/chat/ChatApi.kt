package com.guardianlab.chat

import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.io.File

class ChatApi(val base:String, val token:String="") {
 init {
  val u=URL(base);val h=u.host
  require(u.protocol=="http" && (h=="localhost" || h=="127.0.0.1" || h.startsWith("192.168.") || h.startsWith("10.") || h.matches(Regex("172\\.(1[6-9]|2[0-9]|3[01])\\..*")) || h.endsWith(".local"))) { "Use your Mac's local Wi-Fi address (http://192.168…:8765)" }
  require(u.userInfo==null && u.path in listOf("","/")) {"Enter only the server address"}
 }
 fun request(path:String,body:JSONObject?=null):JSONObject {
  val c=URL(base.trimEnd('/')+path).openConnection() as HttpURLConnection
  try {
   c.connectTimeout=6000;c.readTimeout=20000;c.setRequestProperty("Authorization","Bearer $token")
   if(body!=null){c.requestMethod="POST";c.doOutput=true;c.setRequestProperty("Content-Type","application/json");val bytes=body.toString().toByteArray();c.setFixedLengthStreamingMode(bytes.size);c.outputStream.use {it.write(bytes)}}
   val ok=c.responseCode in 200..299
   val response=(if(ok)c.inputStream else c.errorStream)?.bufferedReader()?.use {it.readText()} ?: "{}"
   val json=JSONObject(response)
   check(ok){json.optString("error","Server error")};return json
  }finally{c.disconnect()}
 }
 fun download(id:String,out:File,viewToken:String=""){
  require(id.matches(Regex("[a-f0-9]{32}")))
  val c=URL(base.trimEnd('/')+"/files/$id").openConnection() as HttpURLConnection
  try {
   c.connectTimeout=6000;c.readTimeout=20000;c.setRequestProperty("Authorization","Bearer $token")
   if(viewToken.isNotEmpty())c.setRequestProperty("X-View-Token",viewToken)
   check(c.responseCode==200){"File unavailable"}
   c.inputStream.use {input->out.outputStream().use {sink->val buffer=ByteArray(65536);var total=0;while(true){val n=input.read(buffer);if(n<0)break;total+=n;check(total<=30*1024*1024){"File exceeds test limit"};sink.write(buffer,0,n)}}}
  }catch(e:Exception){out.delete();throw e}finally{c.disconnect()}
 }
}
