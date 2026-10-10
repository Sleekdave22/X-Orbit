package com.guardianlab.app
import org.junit.Test
import org.junit.Assert.*
import java.nio.file.Files
import java.io.File
class ProtectionDiagnosticsTest {
 @Test fun boundsHistoryAndSuppressesRepeatedState(){
  val dir=Files.createTempDirectory("gl-history").toFile()
  try {
   val d=ProtectionDiagnostics(dir)
   for(i in 0..120)d.sample(i*200L,"\"confidence\":0.4")
   d.transition("phone","confirmed",25000)
   d.transition("phone","confirmed",25100)
   assertTrue(d.finishWrites())
   val lines=File(dir,"events.jsonl").readLines()
   assertEquals(1,lines.size)
   assertEquals(101,Regex("elapsed_ms").findAll(lines.single()).count())
   assertFalse(lines.single().contains("\"elapsed_ms\":0,"))
  }finally{dir.deleteRecursively()}
 }
 @Test fun samplesAreRateLimited(){
  val dir=Files.createTempDirectory("gl-rate").toFile()
  try {
   val d=ProtectionDiagnostics(dir)
   d.sample(0,"\"confidence\":0.1");d.sample(100,"\"confidence\":0.2")
   d.sample(200,"\"confidence\":0.3");d.transition("viewer","clear",200)
   assertTrue(d.finishWrites())
   assertEquals(3,Regex("elapsed_ms").findAll(File(dir,"events.jsonl").readText()).count())
  }finally{dir.deleteRecursively()}
 }
 @Test fun rotatesFilesAndKeepsNewEvent(){
  val dir=Files.createTempDirectory("gl-rotate").toFile()
  try {
   File(dir,"events.jsonl").writeText("x".repeat(512*1024))
   val d=ProtectionDiagnostics(dir);d.transition("phone","confirmed",1)
   assertTrue(d.finishWrites())
   assertEquals(512*1024L,File(dir,"events.previous.jsonl").length())
   assertTrue(File(dir,"events.jsonl").readText().contains("confirmed"))
  }finally{dir.deleteRecursively()}
 }
 @Test fun storageFailureDoesNotPropagate(){
  val file=Files.createTempFile("gl-file","tmp").toFile()
  try{val d=ProtectionDiagnostics(file);d.transition("phone","confirmed",1);assertTrue(d.finishWrites())}finally{file.delete()}
 }
}
