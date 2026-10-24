package com.guardianlab.chat

import org.junit.Assert.*
import org.junit.Test

class PairWallpaperTest {
 @Test fun blueGoldMatchesWebPreviewInBothModes(){
  assertArrayEquals(intArrayOf(0xff1a3f87.toInt(),0xff977830.toInt(),0xff2e250f.toInt()),PairWallpaper.colors(0xff2458bc.toInt(),0xffe8b84a.toInt(),false))
  assertArrayEquals(intArrayOf(0xffb9caea.toInt(),0xfff5e1b3.toInt(),0xfffbf2de.toInt()),PairWallpaper.colors(0xff2458bc.toInt(),0xffe8b84a.toInt(),true))
 }
 @Test fun neutralPairsStayNeutral(){
  for(bright in listOf(false,true))for(color in PairWallpaper.colors(0xff262626.toInt(),0xff000000.toInt(),bright)){
   assertEquals((color ushr 16) and 255,(color ushr 8) and 255)
   assertEquals((color ushr 8) and 255,color and 255)
  }
 }
}
