package com.guardianlab.sdk
import org.junit.Test
import org.junit.Assert.*
class PhoneFrameEvaluatorTest {
 private fun state(i:LightIntensity,c:LightColorCast)=LightingState(i,c,120.0,120.0,.33,.33,.34)
 @Test fun normalNeutralUsesMainAppThreshold(){assertEquals(.40f,PhoneFrameEvaluator.thresholdFor(state(LightIntensity.NORMAL,LightColorCast.NEUTRAL)),0f)}
 @Test fun coloredDarkAndUnknownRemainConservative(){
  for(i in LightIntensity.values())for(c in LightColorCast.values()){
   if(i==LightIntensity.NORMAL && c==LightColorCast.NEUTRAL)continue
   assertEquals(.50f,PhoneFrameEvaluator.thresholdFor(state(i,c)),0f)
  }
 }
 @Test fun midConfidencePhoneAcceptedInNeutralButNotColored(){
  val box=DeviceBox(0f,0f,100f,150f,.45f)
  assertTrue(PhoneFrameEvaluator.qualifies(box,.40f));assertFalse(PhoneFrameEvaluator.qualifies(box,.50f))
 }
 @Test fun undersizedAndOtherClassBoxesDoNotQualify(){
  assertFalse(PhoneFrameEvaluator.qualifies(DeviceBox(0f,0f,49f,100f,.9f),.4f))
  assertFalse(PhoneFrameEvaluator.qualifies(DeviceBox(0f,0f,100f,100f,.9f,"other"),.4f))
 }
 @Test fun lightingStabilizesUsingMainAppRules(){
  val analyzer=LightingAnalyzer();var latest=analyzer.update(120,120,120,120.0)
  repeat(4){latest=analyzer.update(120,120,120,120.0)}
  assertEquals(.4f,PhoneFrameEvaluator.thresholdFor(latest),0f)
 }
}
