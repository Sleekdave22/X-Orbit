package com.guardianlab.sdk
import org.junit.Test
import org.junit.Assert.*
class ProtectionOverrideTest {
 private fun confirm(c:ProtectionController){c.frame(true,0);c.frame(true,100);c.frame(true,200)}
 @Test fun overridesDetectionUntilDeadline(){
  val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=true));confirm(c)
  assertEquals(30L,c.pauseProtection(200).pauseRemainingSeconds)
  for(t in 300L..30_100L step 100){assertFalse(c.frame(true,t).coverContent)}
  assertTrue(c.frame(true,30_200).coverContent)
 }
 @Test fun earlyResumeProtectsAgain(){val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=true));confirm(c);c.pauseProtection(200);assertTrue(c.resumeProtection(300).coverContent)}
 @Test fun missingFramesCancelOverride(){val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=true));confirm(c);c.pauseProtection(200);assertTrue(c.tick(3000).coverContent)}
 @Test fun cameraFailureCancelsOverride(){val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=true));confirm(c);c.pauseProtection(200);assertTrue(c.unavailable().coverContent)}
 @Test fun unusableViewCancelsOverride(){val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=true));confirm(c);c.pauseProtection(200);assertTrue(c.cameraViewUnavailable(300).coverContent)}
 @Test fun defaultHostCannotPause(){val c=ProtectionController();confirm(c);assertTrue(c.pauseProtection(200).coverContent);assertEquals(0L,c.pauseProtection(200).pauseRemainingSeconds)}
 @Test fun strictHostCannotPause(){val c=ProtectionController(ProtectionPolicy(allowTemporaryOverride=false));confirm(c);assertTrue(c.pauseProtection(200).coverContent)}
}
