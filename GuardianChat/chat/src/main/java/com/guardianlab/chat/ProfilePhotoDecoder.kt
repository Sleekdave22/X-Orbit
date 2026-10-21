package com.guardianlab.chat

import android.graphics.Bitmap
import android.graphics.ImageDecoder
import java.nio.ByteBuffer

/** BitmapFactory ignores EXIF on existing avatars; ImageDecoder matches browser orientation. */
internal object ProfilePhotoDecoder {
 fun decode(bytes:ByteArray):Bitmap=ImageDecoder.decodeBitmap(ImageDecoder.createSource(ByteBuffer.wrap(bytes))){decoder,info,_->
  decoder.allocator=ImageDecoder.ALLOCATOR_SOFTWARE
  val edge=maxOf(info.size.width,info.size.height)
  if(edge>1024)decoder.setTargetSize(maxOf(1,info.size.width*1024/edge),maxOf(1,info.size.height*1024/edge))
 }
}
