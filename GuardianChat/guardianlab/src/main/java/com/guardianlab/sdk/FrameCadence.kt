package com.guardianlab.sdk

/** Worker-thread gate; call BEFORE converting a camera frame. Skipped frames must be closed.
 * Caps inference starts, never pauses monitoring because the scene is clear.
 */
class FrameCadence(val maxFramesPerSecond: Int = 5) {
 init { require(maxFramesPerSecond in 1..10) }
 private val intervalMillis = (1000L + maxFramesPerSecond - 1) / maxFramesPerSecond
 private var lastStart: Long? = null
 fun shouldAnalyze(nowMillis: Long): Boolean {
  val last=lastStart
  if(last!=null && nowMillis>=last && nowMillis-last<intervalMillis)return false
  lastStart=nowMillis
  return true
 }
 fun reset(){lastStart=null}
}
