package com.guardianlab.chat

import kotlin.math.roundToInt

/** Same channel mixtures as the web picker; no bitmap or saved artwork is modified. */
internal object PairWallpaper {
 fun colors(first:Int,second:Int,bright:Boolean):IntArray = if(bright)
  intArrayOf(mix(first,255,.32),mix(second,255,.42),mix(second,255,.18))
 else intArrayOf(mix(first,0,.72),mix(second,0,.65),mix(second,0,.2))
 private fun mix(color:Int,base:Int,amount:Double):Int {
  fun channel(shift:Int)=(((color ushr shift) and 255)*amount+base*(1-amount)).roundToInt()
  return (255 shl 24) or (channel(16) shl 16) or (channel(8) shl 8) or channel(0)
 }
}
