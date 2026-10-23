package com.guardianlab.chat

import android.graphics.*
import android.graphics.drawable.Drawable

/** Shared original artwork, centre-cropped without stretching for each appearance. */
internal class OrbitWallpaper(private val dark:Bitmap,private val light:Bitmap,private val bright:()->Boolean):Drawable(){
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
 override fun draw(canvas:Canvas){
  canvas.drawColor(OrbitPalette.color(OrbitPalette.BG,OrbitPalette.LIGHT_BG,bright()))
  if(bounds.isEmpty)return
  val bitmap=if(bright())light else dark
  val scale=maxOf(bounds.width().toFloat()/bitmap.width,bounds.height().toFloat()/bitmap.height)
  val width=bitmap.width*scale;val height=bitmap.height*scale
  val left=bounds.exactCenterX()-width/2;val top=bounds.exactCenterY()-height/2
  val save=canvas.save();canvas.clipRect(bounds)
  canvas.drawBitmap(bitmap,null,RectF(left,top,left+width,top+height),paint)
  canvas.restoreToCount(save)
 }

 override fun setAlpha(alpha:Int){paint.alpha=alpha;invalidateSelf()}
 override fun setColorFilter(filter:ColorFilter?){paint.colorFilter=filter;invalidateSelf()}
 @Deprecated("Required by Drawable") override fun getOpacity()=PixelFormat.OPAQUE
}
