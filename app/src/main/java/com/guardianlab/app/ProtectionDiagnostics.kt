package com.guardianlab.app

import java.io.File
import java.util.concurrent.ArrayBlockingQueue
import java.util.concurrent.ThreadPoolExecutor
import java.util.concurrent.TimeUnit

/** Numeric metadata only. Bounded memory, files and asynchronous write queue. */
class ProtectionDiagnostics(private val directory:File) {
 private val samples=ArrayDeque<String>()
 private var lastSample=Long.MIN_VALUE
 private val states=mutableMapOf<String,String>()
 private val writer=ThreadPoolExecutor(1,1,30,TimeUnit.SECONDS,ArrayBlockingQueue<Runnable>(8),ThreadPoolExecutor.DiscardOldestPolicy()).apply {allowCoreThreadTimeOut(true)}
 internal fun finishWrites():Boolean { writer.shutdown(); return writer.awaitTermination(5,TimeUnit.SECONDS) }
 @Synchronized fun sample(now:Long,fields:String) {
  if(lastSample!=Long.MIN_VALUE && now-lastSample<200)return
  lastSample=now
  samples.addLast("{\"elapsed_ms\":$now,$fields}")
  while(samples.size>100)samples.removeFirst()
 }
 @Synchronized fun transition(source:String,state:String,now:Long,fields:String="") {
  require(source.matches(Regex("[a-z_]+")) && state.matches(Regex("[a-z_]+")))
  if(states[source]==state)return
  states[source]=state
  val extra=if(fields.isEmpty())"" else ",$fields"
  val record="{\"schema\":1,\"wall_ms\":${System.currentTimeMillis()},\"elapsed_ms\":$now,\"source\":\"$source\",\"state\":\"$state\"$extra,\"history\":[${samples.joinToString(",") }]}\n"
  writer.execute {
   try {
    directory.mkdirs()
    val current=File(directory,"events.jsonl")
    if(current.length()+record.toByteArray().size>512*1024){
     val previous=File(directory,"events.previous.jsonl")
     if(previous.exists() && !previous.delete())return@execute
     if(current.exists() && !current.renameTo(previous))return@execute
    }
    current.appendText(record)
   }catch(_:Exception){ /* Diagnostic storage must not interrupt protection. */ }
  }
 }
}
