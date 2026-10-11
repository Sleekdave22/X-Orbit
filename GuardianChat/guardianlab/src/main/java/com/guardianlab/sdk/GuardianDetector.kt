package com.guardianlab.sdk

import android.content.Context
import android.graphics.Bitmap
import ai.onnxruntime.*
import java.nio.FloatBuffer
import java.security.MessageDigest
import kotlin.math.max
import kotlin.math.min

data class DeviceBox(val left: Float, val top: Float, val right: Float, val bottom: Float, val confidence: Float, val deviceClass: String = "phone")
/** CPU-only detector. Supply upright RGB bitmaps on a worker thread. No frame storage or networking. */
class GuardianDetector(context: Context) : AutoCloseable {
 private val environment = OrtEnvironment.getEnvironment()
 private val session: OrtSession
 init {
  val bytes = context.applicationContext.assets.open("guardianlab.onnx").use { it.readBytes() }
  val sha = MessageDigest.getInstance("SHA-256").digest(bytes).joinToString("") { "%02x".format(it) }
  check(sha == "4678cabfc27b3e8477f9ce8926603756cd676f148aebb0ff10f32b1727d4befa") { "GuardianLab model integrity check failed" }
  OrtSession.SessionOptions().use { options ->
   options.setIntraOpNumThreads(2)
   options.setOptimizationLevel(OrtSession.SessionOptions.OptLevel.ALL_OPT)
   session = environment.createSession(bytes, options)
  }
 }
 @Synchronized fun detect(bitmap: Bitmap): List<DeviceBox> {
  val scale = min(640.0 / bitmap.width, 640.0 / bitmap.height)
  val width = Math.rint(bitmap.width * scale).toInt().coerceIn(1,640)
  val height = Math.rint(bitmap.height * scale).toInt().coerceIn(1,640)
  val px = (640-width)/2; val py = (640-height)/2
  val resized = Bitmap.createScaledBitmap(bitmap,width,height,true)
  val pixels = IntArray(width*height)
  resized.getPixels(pixels,0,width,0,0,width,height)
  if (resized !== bitmap) resized.recycle()
  val input = FloatArray(3*640*640) { 114f/255f }
  for (y in 0 until height) for (x in 0 until width) {
   val color=pixels[y*width+x]; val index=(y+py)*640+x+px
   input[index]=((color shr 16) and 255)/255f
   input[640*640+index]=((color shr 8) and 255)/255f
   input[2*640*640+index]=(color and 255)/255f
  }
  val candidates=mutableListOf<DeviceBox>()
  OnnxTensor.createTensor(environment,FloatBuffer.wrap(input),longArrayOf(1,3,640,640)).use { tensor ->
   session.run(mapOf("images" to tensor)).use { results ->
    @Suppress("UNCHECKED_CAST") val output=(results[0].value as Array<Array<FloatArray>>)[0]
    check(output.size==5 && output.all { it.size==8400 }) { "Unsupported model output" }
    val s=scale.toFloat()
    for (i in 0 until 8400) {
     val c=output[4][i]; if (!c.isFinite() || c<0.30f) continue
     val x=output[0][i];val y=output[1][i];val w=output[2][i];val h=output[3][i]
     if (!x.isFinite() || !y.isFinite() || !w.isFinite() || !h.isFinite() || w<=0 || h<=0) continue
     val b=DeviceBox(((x-w/2-px)/s).coerceIn(0f,bitmap.width.toFloat()),((y-h/2-py)/s).coerceIn(0f,bitmap.height.toFloat()),((x+w/2-px)/s).coerceIn(0f,bitmap.width.toFloat()),((y+h/2-py)/s).coerceIn(0f,bitmap.height.toFloat()),c)
     if(b.right>b.left && b.bottom>b.top) candidates.add(b)
    }
   }
  }
  val kept=mutableListOf<DeviceBox>()
  for(b in candidates.sortedByDescending { it.confidence }) {
   if(kept.none { overlap(it,b)>0.50f }) kept.add(b)
   if(kept.size==300) break
  }
  return kept
 }
 private fun overlap(a:DeviceBox,b:DeviceBox):Float {
  val intersection=max(0f,min(a.right,b.right)-max(a.left,b.left))*max(0f,min(a.bottom,b.bottom)-max(a.top,b.top))
  val union=(a.right-a.left)*(a.bottom-a.top)+(b.right-b.left)*(b.bottom-b.top)-intersection
  return if(union>0) intersection/union else 0f
 }
 @Synchronized override fun close() { session.close() }
}
