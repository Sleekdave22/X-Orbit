package com.guardianlab.sdk

import android.graphics.Bitmap
import android.graphics.Color

/** Conservative usability check, not proof of tampering. No images retained. */
class CameraViewEvaluator {
 fun evaluate(bitmap: Bitmap): CameraViewQuality {
  val width=32; val height=24
  val luminance=DoubleArray(width*height)
  for(y in 0 until height) for(x in 0 until width) {
   val pixel=bitmap.getPixel(x*(bitmap.width-1)/(width-1),y*(bitmap.height-1)/(height-1))
   luminance[y*width+x]=0.299*Color.red(pixel)+0.587*Color.green(pixel)+0.114*Color.blue(pixel)
  }
  return assess(luminance,width,height)
 }
 companion object {
  /** Spatial statistics intentionally do not use brightness alone to reject low light. */
  fun assess(luminance:DoubleArray,width:Int,height:Int):CameraViewQuality {
   require(width>=8 && height>=8 && luminance.size==width*height)
   require(luminance.all { it.isFinite() && it in 0.0..255.0 })
   val mean=luminance.average()
   val dark=luminance.count {it<12}/luminance.size.toDouble()
   val bright=luminance.count {it>245}/luminance.size.toDouble()
   var flatTiles=0
   for(ty in 0..3) for(tx in 0..3) {
    var sum=0.0; var squares=0.0; var count=0
    for(y in ty*height/4 until (ty+1)*height/4) for(x in tx*width/4 until (tx+1)*width/4) {
     val value=luminance[y*width+x];sum+=value;squares+=value*value;count++
    }
    val variance=(squares/count-(sum/count)*(sum/count)).coerceAtLeast(0.0)
    if(variance<9.0)flatTiles++
   }
   val reason=when {
    dark>=0.95 && mean<12 -> CameraViewProblem.TOO_DARK
    bright>=0.95 -> CameraViewProblem.OVEREXPOSED
    flatTiles>=12 -> CameraViewProblem.INSUFFICIENT_DETAIL
    else -> null
   }
   return CameraViewQuality(reason==null,reason)
  }
 }
}
enum class CameraViewProblem { TOO_DARK, OVEREXPOSED, INSUFFICIENT_DETAIL }
data class CameraViewQuality(val usable:Boolean,val problem:CameraViewProblem?=null)
