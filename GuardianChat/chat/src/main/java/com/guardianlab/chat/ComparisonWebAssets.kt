package com.guardianlab.chat

import android.content.Context
import android.webkit.WebResourceRequest
import android.webkit.WebResourceResponse
import java.io.ByteArrayInputStream
import java.io.IOException

/** Changes only the comparison WebView's static interface, never its server or TLS policy. */
internal class ComparisonWebAssets(private val context: Context, base: String) {
 private val policy = ComparisonAssetPolicy(base)
 fun response(request: WebResourceRequest): WebResourceResponse? {
  val path = policy.asset(request.method, request.url.toString()) ?: return null
  val mime = when (path.substringAfterLast('.')) {
   "html" -> "text/html"
   "js" -> "text/javascript"
   "css" -> "text/css"
   "png" -> "image/png"
   "ttf" -> "font/ttf"
   else -> return null
  }
  val encoding = if (mime.startsWith("text/")) "utf-8" else null
  val headers = mapOf("Cache-Control" to "no-store", "X-Content-Type-Options" to "nosniff")
  return try {
   WebResourceResponse(mime, encoding, 200, "OK", headers, context.assets.open(path))
  } catch (_: IOException) {
   // Never silently replace a missing comparison page with the other app's design.
   WebResourceResponse("text/plain", "utf-8", 503, "Interface unavailable", headers,
    ByteArrayInputStream("The comparison interface was not packaged. Reinstall X ORBIT Compare.".toByteArray()))
  }
 }
}
