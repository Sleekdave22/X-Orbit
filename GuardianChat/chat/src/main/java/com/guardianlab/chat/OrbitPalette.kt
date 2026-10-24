package com.guardianlab.chat

import android.content.Context
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.GradientDrawable
import android.graphics.drawable.StateListDrawable

/** Visual tokens only. No account, messaging or protection decisions live here. */
internal object OrbitPalette {
 const val BG="#0B1520";const val CARD="#131932";const val CARD2="#202546";const val LINE="#2E3560"
 const val INK="#F1F5F9";const val MUTED="#94A3B8";const val VIOLET="#7C3AED";const val VIOLET_TEXT="#A78BFA"
 const val CYAN="#22D3EE";const val MINT="#34D399";const val AMBER="#FFB822";const val CORAL="#FF7185"
 const val LIGHT_BG="#F4F7FB";const val LIGHT_CARD="#FFFFFF";const val LIGHT_CARD2="#E8EDF6";const val LIGHT_LINE="#C5CEE0"
 const val LIGHT_INK="#0B1520";const val LIGHT_MUTED="#4A5878";const val LIGHT_VIOLET="#6D28D9"
 const val LIGHT_CYAN="#0E7490";const val LIGHT_MINT="#047857";const val LIGHT_CORAL="#BE123C";const val LIGHT_EDGE="#78859F"
 fun color(dark:String,light:String,bright:Boolean)=Color.parseColor(if(bright)light else dark)
 fun focus(context:Context,bright:Boolean)=StateListDrawable().apply {
  val scale=context.resources.displayMetrics.density
  fun shape(stroke:Boolean)=GradientDrawable().apply {setColor(if(stroke)Color.TRANSPARENT else Color.parseColor("#2222D3EE"));cornerRadius=12*scale;if(stroke)setStroke((2*scale).toInt(),color(CYAN,LIGHT_CYAN,bright))}
  addState(intArrayOf(android.R.attr.state_focused),shape(true))
  addState(intArrayOf(android.R.attr.state_pressed),shape(false))
  addState(intArrayOf(),GradientDrawable().apply {setColor(Color.TRANSPARENT)})
 }
}
