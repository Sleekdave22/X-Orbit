package com.guardianlab.chat

/** Comfortable preview space that still leaves the conversation and composer visible. */
internal object AttachmentPreviewLayout {
 fun height(availableHeight:Int,comfortableHeight:Int):Int {
  val available=availableHeight.coerceAtLeast(0)
  return maxOf(available*30/100,comfortableHeight.coerceAtLeast(0))
   .coerceAtMost(available*45/100).coerceAtLeast(1)
 }
}
