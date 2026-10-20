package com.guardianlab.chat

import java.net.URI

/** A fixed static-file allowlist. Account, message, media and competition APIs never match. */
internal class ComparisonAssetPolicy(base: String) {
 private val origin = URI(base)
 private val files = setOf("gaming.html", "gaming.js", "gaming.css", "orbit-theme.css",
  "studio.js", "result-room.js", "orbit-icon.png", "roboto-0.ttf", "roboto-1.ttf", "comparison-compat.js")
 private fun port(uri: URI) = if (uri.port == -1) 443 else uri.port
 fun asset(method: String, address: String): String? = try {
  val uri = URI(address)
  val filename = uri.rawPath.removePrefix("/")
  if (method != "GET" || origin.scheme != "https" || uri.scheme != "https" ||
   uri.host?.equals(origin.host, ignoreCase = true) != true || port(uri) != port(origin) ||
   uri.rawUserInfo != null || uri.rawFragment != null || uri.rawPath != "/$filename" || filename !in files) null
  else "comparison-web/$filename"
 } catch (_: Exception) { null }
}
