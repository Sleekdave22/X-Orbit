package com.guardianlab.chat

import org.junit.Assert.assertEquals
import org.junit.Test

class AttachmentPreviewLayoutTest {
 @Test fun trayShrinksWithKeyboardAndRotation(){
  assertEquals(120,AttachmentPreviewLayout.height(600))
  assertEquals(60,AttachmentPreviewLayout.height(300))
  assertEquals(180,AttachmentPreviewLayout.height(900))
 }
 @Test fun unmeasuredChatDoesNotRequestMatchParentOrWrapContent(){
  assertEquals(1,AttachmentPreviewLayout.height(0))
  assertEquals(1,AttachmentPreviewLayout.height(-1))
 }
}
