package com.guardianlab.sdk
import org.junit.Test
import org.junit.Assert.*
class ProtectionTest {
 private fun clear(c:ProtectionController,start:Long) { for(t in start..start+3000 step 500)c.frame(false,t) }
 private fun confirm(c:ProtectionController,start:Long) {c.frame(true,start);c.frame(true,start+100);c.frame(true,start+200)}
 @Test fun startsCoveredUntilThreeClearSeconds() {
  val c=ProtectionController(); assertTrue(c.frame(false,0).coverContent)
  for(t in 500L..2500L step 500)assertTrue(c.frame(false,t).coverContent)
  assertFalse(c.frame(false,3000).coverContent)
 }
 @Test fun defaultRestoresAutomaticallyAfterConfirmedDeviceClears() {
  val c=ProtectionController();confirm(c,0); assertTrue(c.tick(200).coverContent)
  clear(c,300);assertFalse(c.tick(3300).coverContent)
 }
 @Test fun manualModeRequiresExplicitResume() {
  val c=ProtectionController(ProtectionPolicy(manualResume=true));confirm(c,0)
  clear(c,300);assertEquals(ProtectionState.READY_TO_RESUME,c.tick(3300).state)
  assertTrue(c.tick(3300).coverContent);assertFalse(c.resume(3300).coverContent)
 }
 @Test fun reappearingDeviceRestartsClearCountdown() {
  val c=ProtectionController();confirm(c,0)
  for(t in 300L..2800L step 500)c.frame(false,t)
  c.frame(true,2900)
  for(t in 3000L..5500L step 500)assertTrue(c.frame(false,t).coverContent)
  assertFalse(c.frame(false,6000).coverContent)
 }
 @Test fun missingFramesCannotUnblur() {
  val c=ProtectionController();confirm(c,0);c.frame(false,300)
  assertTrue(c.tick(4000).coverContent)
  assertEquals(ProtectionState.MONITORING_UNAVAILABLE,c.tick(4000).state)
  assertTrue(c.frame(false,4100).coverContent)
 }
 @Test fun staleManualResumeCannotReveal() {
  val c=ProtectionController(ProtectionPolicy(manualResume=true));confirm(c,0);clear(c,300)
  assertTrue(c.resume(6000).coverContent)
 }
 @Test fun firstCandidateImmediatelyBlursClearContent() {
  val c=ProtectionController();clear(c,0);assertTrue(c.frame(true,3100).coverContent)
 }
 @Test fun cameraFailureCoversAndRequiresNewClearPeriod() {
  val c=ProtectionController();clear(c,0);assertTrue(c.unavailable().coverContent)
  clear(c,4000);assertFalse(c.tick(7000).coverContent)
 }
 @Test fun reentryAfterLongClearPeriodNeverReinitializes() {
  val c=ProtectionController();for(t in 0L..60000L step 500)c.frame(false,t)
  val first=c.frame(true,60100);assertTrue(first.coverContent)
  assertEquals(ProtectionState.POSSIBLE_DEVICE,first.state)
  assertEquals(ProtectionState.WAITING_FOR_CLEAR,c.frame(false,60200).state)
  c.frame(true,60300);assertEquals(ProtectionState.DEVICE_CONFIRMED,c.frame(true,60400).state)
 }
 @Test fun candidateClearNeedsThreeUninterruptedSeconds() {
  val c=ProtectionController();clear(c,0);c.frame(true,3100)
  for(t in 3200L..5700L step 500)assertTrue(c.frame(false,t).coverContent)
  assertFalse(c.frame(false,6200).coverContent)
 }
 @Test fun hostsCanOptOutOfCandidateCoverWithoutReinitializing() {
  val c=ProtectionController(ProtectionPolicy(coverOnCandidate=false));clear(c,0)
  assertFalse(c.frame(true,3100).coverContent)
  assertEquals(ProtectionState.CLEAR,c.frame(false,3200).state)
 }
 @Test fun thresholdSwitchDiscardsVotesWithoutRevealingContent(){
  val c=ProtectionController();c.frame(true,0);c.frame(true,100);c.resetConfirmationHistory()
  assertTrue(c.frame(false,200).coverContent)
  assertEquals(ProtectionState.POSSIBLE_DEVICE,c.frame(true,300).state)
  assertEquals(ProtectionState.POSSIBLE_DEVICE,c.frame(true,400).state)
  assertEquals(ProtectionState.DEVICE_CONFIRMED,c.frame(true,500).state)
 }
 @Test fun policyChangeStartsCovered() {
  val c=ProtectionController();clear(c,0)
  val strict=ProtectionController(ProtectionPolicy(manualResume=true))
  assertTrue(strict.tick(3000).coverContent)
 }
}
