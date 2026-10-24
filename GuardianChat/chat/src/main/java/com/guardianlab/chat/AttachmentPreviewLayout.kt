package com.guardianlab.chat

/** Share of the available chat area, recalculated when the keyboard resizes it. */
internal object AttachmentPreviewLayout {
 fun height(availableHeight:Int):Int=(availableHeight.coerceAtLeast(0)/5).coerceAtLeast(1)
}
