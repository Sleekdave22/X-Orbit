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
 private var first=Color.parseColor("#22D3EE");private var firstInk=Color.parseColor("#0B1520");private var second=Color.parseColor("#202546");private var secondInk=Color.parseColor("#F1F5F9")
 init {
  textOn="";textOff="";text="";contentDescription="Send as view once"
  minWidth=0;minimumWidth=0;minHeight=0;minimumHeight=0;setPadding(0,0,0,0);backgroundTintList=null
  setPair(first,firstInk,second,secondInk)
 }
 fun setPair(primary:Int,primaryInk:Int,secondary:Int,secondaryInk:Int){
  first=primary;firstInk=primaryInk;second=secondary;secondInk=secondaryInk
  background=null
  invalidate()
 }
 override fun onDraw(canvas:Canvas){
  val edge=minOf(width,height,(20*resources.displayMetrics.density).toInt())
  val left=(width-edge)/2;val top=(height-edge)/2
  symbol.setTint(if(isChecked)Color.parseColor("#A78BFA") else secondInk);symbol.setBounds(left,top,left+edge,top+edge);symbol.draw(canvas)
 }
}
