package com.guardianlab.chat

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable
import android.widget.ToggleButton

/** A single-use “1” and broken orbit, with the usual accessible checked state. */
internal class OnceToggle(context:Context):ToggleButton(context){
 private val symbol=context.getDrawable(R.drawable.ic_view_once)!!.mutate()
 init {
  textOn="";textOff="";text="";contentDescription="Send as view once"
  minWidth=0;minimumWidth=0;minHeight=0;minimumHeight=0;setPadding(0,0,0,0);backgroundTintList=null
  fun shape(color:Int)=GradientDrawable().apply {setColor(color);cornerRadius=10*resources.displayMetrics.density}
  background=StateListDrawable().apply {addState(intArrayOf(android.R.attr.state_checked),shape(Color.parseColor("#e8b84a")));addState(intArrayOf(),shape(Color.parseColor("#343034")))}
 }
 override fun onDraw(canvas:Canvas){
  val edge=minOf(width,height,(28*resources.displayMetrics.density).toInt())
  val left=(width-edge)/2;val top=(height-edge)/2
  symbol.setTint(if(isChecked)Color.parseColor("#4a1020") else Color.parseColor("#e8b84a"));symbol.setBounds(left,top,left+edge,top+edge);symbol.draw(canvas)
 }
}
