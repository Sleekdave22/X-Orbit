package com.guardianlab.app

import android.graphics.BitmapFactory
import android.graphics.Bitmap
import android.graphics.Matrix
import ai.onnxruntime.OnnxTensor
import java.nio.FloatBuffer
import java.nio.ByteBuffer
import java.nio.ByteOrder
import androidx.test.platform.app.InstrumentationRegistry
import androidx.test.ext.junit.runners.AndroidJUnit4
import org.junit.Test
import org.junit.runner.RunWith
import org.junit.Assert.*
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import kotlin.math.abs

@RunWith(AndroidJUnit4::class)
class Yolo26ParityTest {
    private fun writeFloats(file: File, values: FloatArray) {
        val buffer = ByteBuffer.allocate(values.size * 4).order(ByteOrder.LITTLE_ENDIAN)
        buffer.asFloatBuffer().put(values)
        file.writeBytes(buffer.array())
    }
    @Test fun referenceImagesRepeated() {
        val inst = InstrumentationRegistry.getInstrumentation()
        val assets = inst.context.assets
        val reference = JSONObject(assets.open("yolo26_parity/reference.json").bufferedReader().use { it.readText() })
        val rows = reference.getJSONArray("rows")
        assertEquals(36, rows.length())
        val loader = ModelLoader(inst.targetContext)
        try {
            val detector = YOLODetector(loader)
            val outputs = JSONArray()
            for (i in 0 until rows.length()) {
                val row = rows.getJSONObject(i)
                val name = row.getString("image")
                val label = row.getString("label")
                val decoded = assets.open("yolo26_parity/images/$label/$name").use { BitmapFactory.decodeStream(it) }
                assertNotNull(decoded)
                val orientation = row.getInt("exif_orientation")
                assertTrue("Supported orientation", orientation == 1 || orientation == 8)
                val bitmap = if (orientation == 8) {
                    val matrix = Matrix().apply { postRotate(-90f) }
                    Bitmap.createBitmap(decoded, 0, 0, decoded.width, decoded.height, matrix, true).also { decoded.recycle() }
                } else decoded
                val tensorDir = File(inst.targetContext.filesDir, "yolo26_aligned_tensors").apply { mkdirs() }
                val scale = minOf(640.0 / bitmap.width, 640.0 / bitmap.height)
                val rw = Math.rint(bitmap.width * scale).toInt().coerceIn(1, 640)
                val rh = Math.rint(bitmap.height * scale).toInt().coerceIn(1, 640)
                val resized = Bitmap.createScaledBitmap(bitmap, rw, rh, true)
                val pixels = IntArray(rw * rh)
                resized.getPixels(pixels, 0, rw, 0, 0, rw, rh)
                val input = FloatArray(3 * 640 * 640) { 114f / 255f }
                val px = ((640 - rw) / 2f).toInt()
                val py = ((640 - rh) / 2f).toInt()
                for (y in 0 until rh) for (x in 0 until rw) {
                    val pixel = pixels[y * rw + x]
                    val k = (y + py) * 640 + x + px
                    input[k] = ((pixel shr 16) and 255) / 255f
                    input[640 * 640 + k] = ((pixel shr 8) and 255) / 255f
                    input[2 * 640 * 640 + k] = (pixel and 255) / 255f
                }
                writeFloats(File(tensorDir, "$i.input.bin"), input)
                var tensorTop = 0f
                OnnxTensor.createTensor(loader.getEnvironment(), FloatBuffer.wrap(input), longArrayOf(1, 3, 640, 640)).use { tensor ->
                    loader.getSession().run(mapOf("images" to tensor)).use { result ->
                        val output = result[0].value as Array<Array<FloatArray>>
                        assertEquals(5, output[0].size)
                        assertEquals(8400, output[0][0].size)
                        tensorTop = output[0][4].maxOrNull()!!
                        writeFloats(File(tensorDir, "$i.output.bin"), output[0].flatMap { it.asIterable() }.toFloatArray())
                    }
                }
                val runs = JSONArray()
                repeat(3) {
                    val start = android.os.SystemClock.elapsedRealtime()
                    val result = detector.detectFrame(bitmap)
                    val boxes = JSONArray()
                    for (d in result.detections) {
                        assertTrue(d.confidence.isFinite())
                        boxes.put(JSONObject().put("confidence", d.confidence.toDouble())
                            .put("xyxy", JSONArray(listOf(d.x1, d.y1, d.x2, d.y2))))
                    }
                    val top = (result.detections + result.proposals).maxByOrNull { it.confidence }
                    assertEquals("Exported tensor reproduces production score", tensorTop, top?.confidence ?: 0f, 0.000001f)
                    runs.put(JSONObject().put("top_conf", (top?.confidence ?: 0f).toDouble())
                        .put("top_box", if (top == null) JSONObject.NULL else JSONArray(listOf(top.x1, top.y1, top.x2, top.y2)))
                        .put("detection_count", result.detections.size).put("detections", boxes)
                        .put("duration_ms", android.os.SystemClock.elapsedRealtime() - start))
                }
                outputs.put(JSONObject().put("image", name).put("label", label)
                    .put("width", bitmap.width).put("height", bitmap.height)
                    .put("reference_onnx_top_conf", row.getDouble("onnx_top_conf")).put("runs", runs))
                bitmap.recycle()
            }
            val report = JSONObject().put("model", "guardianlab_yolo26_epoch45_ONE2MANY.onnx")
                .put("rows", outputs)
            File(inst.targetContext.filesDir, "yolo26_android_aligned_parity.json").writeText(report.toString(2))
            for (i in 0 until outputs.length()) {
                val runs = outputs.getJSONObject(i).getJSONArray("runs")
                val first = runs.getJSONObject(0).getDouble("top_conf")
                for (j in 1..2) assertTrue("Repeat stability: ${outputs.getJSONObject(i).getString("image")}",
                    abs(first - runs.getJSONObject(j).getDouble("top_conf")) <= 0.00001)
            }
        } finally { loader.close() }
    }
}
