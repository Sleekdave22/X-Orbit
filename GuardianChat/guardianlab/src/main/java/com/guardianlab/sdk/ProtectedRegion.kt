package com.guardianlab.sdk

import android.content.Context
import android.graphics.*
import android.util.AttributeSet
import android.view.View
import android.widget.FrameLayout

/** Wrap exactly the content the host marks sensitive. Starts protected.
 * Frosted mask uses synthetic pixels; it never samples or stores the sensitive view.
 * This avoids revealing text through a weak blur or retaining it in a screenshot bitmap.
 * Host app must also protect exports, caches, notifications and accessibility elsewhere.
 */
class ProtectedRegion @JvmOverloads constructor(context: Context, attrs: AttributeSet? = null): FrameLayout(context,attrs) {
 private val mask=FrostedMask(context)
 private var protected=true
 init { super.addView(mask,LayoutParams(-1,-1)) }
 override fun onViewAdded(child:View) {
  super.onViewAdded(child)
  if(child!==mask) {
   child.visibility=if(protected)View.INVISIBLE else View.VISIBLE
   child.importantForAccessibility=if(protected)View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS else View.IMPORTANT_FOR_ACCESSIBILITY_AUTO
   mask.bringToFront()
  }
 }
 fun setProtected(value:Boolean) {
  protected=value
  for(i in 0 until childCount) {
   val child=getChildAt(i)
   if(child!==mask) {
    child.visibility=if(value)View.INVISIBLE else View.VISIBLE
    child.importantForAccessibility=if(value)View.IMPORTANT_FOR_ACCESSIBILITY_NO_HIDE_DESCENDANTS else View.IMPORTANT_FOR_ACCESSIBILITY_AUTO
   }
  }
  mask.visibility=if(value)View.VISIBLE else View.GONE
  mask.bringToFront()
 }
 private class FrostedMask(context:Context):View(context) {
  private val paint=Paint(Paint.ANTI_ALIAS_FLAG)
  init { isClickable=true;isFocusable=true;contentDescription="Sensitive content blurred" }
  override fun onDraw(canvas:Canvas) {
   super.onDraw(canvas)
   paint.shader=LinearGradient(0f,0f,width.toFloat(),height.toFloat(),Color.rgb(218,229,234),Color.rgb(188,207,217),Shader.TileMode.CLAMP)
   canvas.drawRect(0f,0f,width.toFloat(),height.toFloat(),paint)
   paint.shader=null
   val w=width.toFloat();val h=height.toFloat()
   for(i in 0..8) {
    val y=h*(0.12f+i*0.085f)
    paint.shader=RadialGradient(w*(if(i%2==0)0.38f else 0.64f),y,w*0.45f,intArrayOf(Color.argb(45,130,151,164),Color.TRANSPARENT),null,Shader.TileMode.CLAMP)
    canvas.drawRect(0f,y-h*0.055f,w,y+h*0.055f,paint)
   }
   paint.shader=null
  }
 }
}
