package com.guardianlab.sdk

import android.graphics.Bitmap
import android.graphics.Color

/** Main GuardianLab's lighting-dependent qualification. One instance per camera session. */
data class PhoneQualification(val phonePresent:Boolean,val confidenceThreshold:Float,val lighting:LightingState)
class PhoneFrameEvaluator {
 private val lighting=LightingAnalyzer()
 fun evaluate(upright:Bitmap,boxes:List<DeviceBox>):PhoneQualification {
  var r=0L;var g=0L;var b=0L;var samples=0
  for(y in 0 until upright.height step 20)for(x in 0 until upright.width step 20){
   val pixel=upright.getPixel(x,y);r+=Color.red(pixel);g+=Color.green(pixel);b+=Color.blue(pixel);samples++
  }
  val avgR=(r/samples).toInt();val avgG=(g/samples).toInt();val avgB=(b/samples).toInt()
  val state=lighting.update(avgR,avgG,avgB,0.299*avgR+0.587*avgG+0.114*avgB)
  val threshold=thresholdFor(state)
  return PhoneQualification(boxes.any {qualifies(it,threshold)},threshold,state)
 }
 companion object {
  fun thresholdFor(state:LightingState):Float =
   if(state.intensity==LightIntensity.NORMAL && state.colorCast==LightColorCast.NEUTRAL)0.40f else 0.50f
  fun qualifies(box:DeviceBox,threshold:Float):Boolean = box.deviceClass=="phone" && box.confidence>=threshold && box.right-box.left>=50f && box.bottom-box.top>=50f
 }
}
