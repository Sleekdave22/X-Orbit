package com.guardianlab.chat

import org.junit.Assert.assertEquals
import org.junit.Test

class AttachmentPreviewLayoutTest {
 @Test fun trayShrinksWithKeyboardAndRotation(){
  assertEquals(180,AttachmentPreviewLayout.height(600,144))
  assertEquals(135,AttachmentPreviewLayout.height(300,144))
  assertEquals(270,AttachmentPreviewLayout.height(900,144))
  assertEquals(144,AttachmentPreviewLayout.height(400,144))
 }
 @Test fun unmeasuredChatDoesNotRequestMatchParentOrWrapContent(){
  assertEquals(1,AttachmentPreviewLayout.height(0,144))
  assertEquals(1,AttachmentPreviewLayout.height(-1,144))
 }
 @Test fun comfortableHeightUsesDevicePixelsAndLeavesRoomForTheChat(){
  assertEquals(540,AttachmentPreviewLayout.height(1800,432))
  assertEquals(405,AttachmentPreviewLayout.height(900,432))
  assertEquals(90,AttachmentPreviewLayout.height(200,144))
 }
}
