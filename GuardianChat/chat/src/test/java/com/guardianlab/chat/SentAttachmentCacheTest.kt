package com.guardianlab.chat

import org.junit.Assert.*
import org.junit.Rule
import org.junit.Test
import org.junit.rules.TemporaryFolder

class SentAttachmentCacheTest {
 @get:Rule val folder=TemporaryFolder()
 @Test fun acknowledgedFileSurvivesPreviewDeletionAndRestart(){
  val preview=folder.newFile("voice.m4a").apply {writeBytes(byteArrayOf(1,2,3))}
  val cache=SentAttachmentCache(folder.root,"https://server:8766","sender")
  cache.save(41,preview.readBytes());preview.delete()
  assertArrayEquals(byteArrayOf(1,2,3),SentAttachmentCache(folder.root,"https://server:8766/","sender").find(41)!!.readBytes())
  cache.save(42,byteArrayOf(4));assertTrue(cache.find(41)!!.exists());assertTrue(cache.find(42)!!.exists())
 }
 @Test fun accountsAndServersCannotReadEachOthersSentFiles(){
  val own=SentAttachmentCache(folder.root,"https://one","sender");own.save(1,byteArrayOf(1))
  assertNull(SentAttachmentCache(folder.root,"https://one","other").find(1))
  assertNull(SentAttachmentCache(folder.root,"https://two","sender").find(1))
 }
 @Test fun viewOnceAndProtectedFilesAreNeverRetainedHere(){
  val cache=SentAttachmentCache(folder.root,"https://one","sender")
  cache.save(1,byteArrayOf(1),viewOnce=true);cache.save(2,byteArrayOf(2),protectedMedia=true)
  assertNull(cache.find(1));assertNull(cache.find(2));assertNull(cache.find(-1))
 }
 @Test fun deletionAndLogoutRemoveOnlyThisAccountsFiles(){
  val own=SentAttachmentCache(folder.root,"https://one","sender");val other=SentAttachmentCache(folder.root,"https://one","other")
  own.save(1,byteArrayOf(1));own.save(2,byteArrayOf(2));other.save(1,byteArrayOf(3))
  own.remove(1);assertNull(own.find(1));assertNotNull(own.find(2))
  own.clear();assertNull(own.find(2));assertNotNull(other.find(1))
 }
 @Test fun boundedCacheKeepsTheNewestAcknowledgedFile(){
  val cache=SentAttachmentCache(folder.root,"https://one","sender",3)
  cache.save(1,byteArrayOf(1,2,3));cache.save(2,byteArrayOf(4,5,6))
  assertNull(cache.find(1));assertArrayEquals(byteArrayOf(4,5,6),cache.find(2)!!.readBytes())
 }
}
