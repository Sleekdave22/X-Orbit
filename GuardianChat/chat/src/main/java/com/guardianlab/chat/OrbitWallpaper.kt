package com.guardianlab.chat

import android.graphics.*
import android.graphics.drawable.Drawable

/** One shared bitmap; draw at its original aspect ratio with a theme-aware scrim. */
internal class OrbitWallpaper(private val bitmap:Bitmap,private val bright:()->Boolean):Drawable(){
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
 override fun draw(canvas:Canvas){
  canvas.drawColor(OrbitPalette.color(OrbitPalette.BG,OrbitPalette.LIGHT_BG,bright()))
  if(!bright()){
   paint.shader=RadialGradient(bounds.exactCenterX(),bounds.top.toFloat(),bounds.width().toFloat().coerceAtLeast(1f),intArrayOf(Color.parseColor("#187C3AED"),Color.TRANSPARENT),null,Shader.TileMode.CLAMP)
   canvas.drawRect(bounds,paint);paint.shader=null
  }
 }

 override fun setAlpha(alpha:Int){paint.alpha=alpha;invalidateSelf()}
 override fun setColorFilter(filter:ColorFilter?){paint.colorFilter=filter;invalidateSelf()}
 @Deprecated("Required by Drawable") override fun getOpacity()=PixelFormat.OPAQUE
}
