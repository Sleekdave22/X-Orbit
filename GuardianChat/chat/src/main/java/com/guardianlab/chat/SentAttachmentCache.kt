package com.guardianlab.chat

import java.io.File
import java.security.MessageDigest
import java.util.UUID

/** App-private ordinary uploads, isolated by server/account and retained across activity restarts. */
internal class SentAttachmentCache(root:File,server:String,account:String,private val maxBytes:Long=256L*1024*1024) {
 private val scope=MessageDigest.getInstance("SHA-256").digest((server.trimEnd('/')+"\n"+account).toByteArray()).joinToString(""){"%02x".format(it)}
 private val directory=File(root,"sent-attachments/$scope")
 private fun path(messageId:Long):File {require(messageId>0);return File(directory,messageId.toString())}
 fun find(messageId:Long):File?=if(messageId>0)path(messageId).takeIf {it.isFile} else null
 fun save(messageId:Long,data:ByteArray,viewOnce:Boolean=false,protectedMedia:Boolean=false) {
  if(viewOnce||protectedMedia)return
  require(data.size<=30*1024*1024)
  val target=path(messageId);check(directory.isDirectory||directory.mkdirs())
  val temporary=File(directory,UUID.randomUUID().toString()+".part")
  try {temporary.writeBytes(data);check(temporary.renameTo(target)){"Could not retain the sent attachment"}} finally {temporary.delete()}
  // Never evict the upload just acknowledged, even if a caller configures a tiny budget.
  val files=directory.listFiles()?.filter {it.isFile&&!it.name.endsWith(".part")}?:return
  var total=files.sumOf {it.length()}
  for(old in files.filter {it!=target}.sortedBy {it.lastModified()}){if(total<=maxBytes)break;val size=old.length();if(old.delete())total-=size}
 }
 fun remove(messageId:Long){if(messageId>0)path(messageId).delete()}
 fun clear(){directory.deleteRecursively()}
}
