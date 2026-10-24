package com.guardianlab.chat

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.View

/** Decorative left/right halves; the adjacent row provides the accessible pair name. */
internal class PairSwatch(context:Context,private val first:Int,private val second:Int):View(context){
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
 init {importantForAccessibility=IMPORTANT_FOR_ACCESSIBILITY_NO}
 override fun onDraw(canvas:Canvas){
  val radius=minOf(width,height)/2f-2*resources.displayMetrics.density
  if(radius<=0)return
  val x=width/2f;val y=height/2f;val circle=RectF(x-radius,y-radius,x+radius,y+radius)
  paint.style=Paint.Style.FILL;paint.color=first;canvas.drawArc(circle,90f,180f,true,paint)
  paint.color=second;canvas.drawArc(circle,270f,180f,true,paint)
  paint.style=Paint.Style.STROKE;paint.strokeWidth=resources.displayMetrics.density;paint.color=Color.parseColor("#8094A3B8");canvas.drawOval(circle,paint)
 }
}
