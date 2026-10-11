package com.guardianlab.sdk
import org.junit.Assert.*
import org.junit.Test
class CameraViewEvaluatorTest {
 private fun quality(value:(Int,Int)->Double)=CameraViewEvaluator.assess(DoubleArray(768){value(it%32,it/32)},32,24)
 @Test fun blackRejected(){assertEquals(CameraViewProblem.TOO_DARK,quality {_,_->2.0}.problem)}
 @Test fun whiteoutRejected(){assertEquals(CameraViewProblem.OVEREXPOSED,quality {_,_->252.0}.problem)}
 @Test fun featurelessRejected(){assertFalse(quality {_,_->85.0}.usable)}
 @Test fun dimDetailedAccepted(){assertTrue(quality {x,y->if((x+y)%2==0)15.0 else 35.0}.usable)}
 @Test fun normalDetailedAccepted(){assertTrue(quality {x,y->if((x+y)%2==0)60.0 else 130.0}.usable)}
 @Test fun mostlyCoveredRejected(){assertFalse(quality {x,y->if(x<24)80.0 else if((x+y)%2==0)40.0 else 130.0}.usable)}
 @Test fun obstructionRequiresFreshClearPeriod(){
  val c=ProtectionController();for(t in 0L..3000L step 1000)c.frame(false,t)
  assertFalse(c.tick(3001).coverContent)
  assertEquals(ProtectionState.CAMERA_VIEW_UNAVAILABLE,c.cameraViewUnavailable(3200).state)
  c.cameraViewUnavailable(5000)
  for(t in 5200L..7200L step 1000)assertTrue(c.frame(false,t).coverContent)
  assertFalse(c.frame(false,8200).coverContent)
 }
 @Test fun blockedCannotResume(){
  val c=ProtectionController(ProtectionPolicy(manualResume=true))
  for(t in 0L..10000L step 200)assertTrue(c.cameraViewUnavailable(t).coverContent)
  assertTrue(c.resume(10100).coverContent)
  for(t in 10200L..12200L step 1000)c.frame(false,t)
  assertEquals(ProtectionState.READY_TO_RESUME,c.frame(false,13200).state)
  assertFalse(c.resume(13201).coverContent)
 }
 @Test fun staleCoveredFramesFailClosed(){val c=ProtectionController();c.cameraViewUnavailable(0);assertEquals(ProtectionState.MONITORING_UNAVAILABLE,c.tick(2000).state)}
}
