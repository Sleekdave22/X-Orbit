package com.guardianlab.chat
import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.graphics.RectF
import android.view.View
/** Actual transfer progress, no invented percentage before the length is known. */
class DownloadRing(context:Context,private val arrow:Boolean=false):View(context){
 private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
 private var fraction:Float?=null
 fun update(bytes:Long,total:Long){fraction=if(total>0)(bytes.toFloat()/total).coerceIn(0f,1f) else null;contentDescription=if(fraction==null)"Downloading"else "Downloaded ${(fraction!!*100).toInt()} percent";invalidate()}
 override fun onDraw(canvas:Canvas){super.onDraw(canvas);val edge=minOf(width,height).toFloat();val stroke=edge*.07f;val rect=RectF(stroke,stroke,width-stroke,height-stroke);paint.style=Paint.Style.STROKE;paint.strokeWidth=stroke;paint.color=Color.rgb(65,65,65);canvas.drawOval(rect,paint);paint.color=Color.rgb(183,43,81);canvas.drawArc(rect,-90f,360f*(fraction?:.15f),false,paint);paint.style=Paint.Style.FILL;paint.textAlign=Paint.Align.CENTER;paint.textSize=edge*.24f;if(arrow){paint.textSize=edge*.4f;canvas.drawText("↓",width/2f,height*.48f-(paint.ascent()+paint.descent())/2,paint);paint.textSize=edge*.19f;canvas.drawText(fraction?.let {"${(it*100).toInt()}%"}?:"",width/2f,height*.83f,paint);return};canvas.drawText(fraction?.let {"${(it*100).toInt()}%"}?:"↓",width/2f,height/2f-(paint.ascent()+paint.descent())/2,paint)}
}
