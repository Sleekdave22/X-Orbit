package com.guardianlab.chat

import android.graphics.*
import android.graphics.drawable.Drawable

/** One shared bitmap; draw at its original aspect ratio with a theme-aware scrim. */
internal class OrbitWallpaper(private val bitmap:Bitmap,private val bright:()->Boolean):Drawable(){
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG or Paint.FILTER_BITMAP_FLAG)
 override fun draw(canvas:Canvas){
  val scale=maxOf(bounds.width().toFloat()/bitmap.width,bounds.height().toFloat()/bitmap.height)
  val width=bitmap.width*scale;val height=bitmap.height*scale
  val left=bounds.left+(bounds.width()-width)/2;val top=bounds.top+(bounds.height()-height)/2
  canvas.drawBitmap(bitmap,null,RectF(left,top,left+width,top+height),paint)
  canvas.drawColor(if(bright())Color.argb(235,247,238,224) else Color.argb(55,27,7,9))
 }
 override fun setAlpha(alpha:Int){paint.alpha=alpha;invalidateSelf()}
 override fun setColorFilter(filter:ColorFilter?){paint.colorFilter=filter;invalidateSelf()}
 @Deprecated("Required by Drawable") override fun getOpacity()=PixelFormat.OPAQUE
}
