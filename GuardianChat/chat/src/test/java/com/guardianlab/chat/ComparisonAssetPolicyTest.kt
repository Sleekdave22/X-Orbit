package com.guardianlab.chat

import org.junit.Assert.*
import org.junit.Test

class ComparisonAssetPolicyTest {
 private val policy = ComparisonAssetPolicy("https://192.168.1.171:8766")
 @Test fun ownStaticFilesUseBundledInterface() {
  assertEquals("comparison-web/gaming.html", policy.asset("GET", "https://192.168.1.171:8766/gaming.html?league=abc"))
  assertEquals("comparison-web/orbit-theme.css", policy.asset("GET", "https://192.168.1.171:8766/orbit-theme.css"))
 }
 @Test fun wallpaperAssetsRemainStaticAndOriginBound() {
  for (file in listOf("orbit-wallpaper.png", "orbit-wallpaper-v2.png")) {
   assertEquals("comparison-web/branding/"+file, policy.asset("GET", "https://192.168.1.171:8766/branding/"+file+"?v=19"))
   assertNull(policy.asset("GET", "https://example.com:8766/branding/"+file))
   assertNull(policy.asset("GET", "https://192.168.1.171:8766/branding/../branding/"+file))
  }
  assertNull(policy.asset("GET", "https://192.168.1.171:8766/branding/private.png"))
 }
 @Test fun APIsAndMediaAlwaysReachServer() {
  for (path in listOf("/", "/profile", "/gamebox/summary", "/gaming/summary", "/messages", "/files/123", "/calls", "/wallet/me"))
   assertNull(path, policy.asset("GET", "https://192.168.1.171:8766$path"))
  assertNull(policy.asset("POST", "https://192.168.1.171:8766/gaming.html"))
 }
 @Test fun foreignOriginsAndEncodedTraversalAreRejected() {
  for (url in listOf("http://192.168.1.171:8766/gaming.html", "https://example.com:8766/gaming.html",
   "https://192.168.1.171:443/gaming.html", "https://user@192.168.1.171:8766/gaming.html",
   "https://192.168.1.171:8766/../gaming.html", "https://192.168.1.171:8766/%67aming.html",
   "https://192.168.1.171:8766/gaming.html#fragment", "not a url")) assertNull(url, policy.asset("GET", url))
 }
 @Test fun defaultHttpsPortMatchesExplicit443() {
  assertEquals("comparison-web/gaming.html", ComparisonAssetPolicy("https://example.com").asset("GET", "https://example.com:443/gaming.html"))
 }
}
