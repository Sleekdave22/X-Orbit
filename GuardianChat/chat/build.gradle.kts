plugins { alias(libs.plugins.android.application) }
android {
 namespace = "com.guardianlab.chat"
 compileSdk { version = release(36) { minorApiLevel = 1 } }
 defaultConfig { applicationId = "com.guardianlab.chat.compare"; minSdk = 29; targetSdk = 36; versionCode = 2; versionName = "0.2-xorbit-compare"; buildConfigField("boolean", "COMPARISON_INTERFACE", "true"); ndk { abiFilters += "arm64-v8a" } }
 buildFeatures { buildConfig = true }
 sourceSets.getByName("main").assets.srcDir(layout.buildDirectory.dir("generated/comparison-assets").get().asFile)
 compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies {
 implementation("com.google.firebase:firebase-messaging:25.1.3")
 implementation(project(":guardianlab"))
 implementation(project(":guardianlab-ui"))
 implementation("androidx.activity:activity-ktx:1.8.0")
 implementation("androidx.camera:camera-camera2:1.6.1")
 implementation("androidx.camera:camera-lifecycle:1.6.1")
 implementation("com.google.mlkit:face-detection:16.1.7")
 testImplementation("junit:junit:4.13.2")
}

// Package the fork's own interface; API calls still use the configured HTTPS server.
val comparisonAssets = tasks.register<Sync>("packageComparisonInterface") {
 from(rootProject.file("server")) {
  include("gaming.html", "gaming.js", "gaming.css", "orbit-theme.css", "studio.js",
   "result-room.js", "orbit-icon.png", "roboto-0.ttf", "roboto-1.ttf", "comparison-compat.js")
 }
 into(layout.buildDirectory.dir("generated/comparison-assets/comparison-web"))
 doLast {
  val page = destinationDir.resolve("gaming.html")
  val source = page.readText()
  check(source.contains("<script src=\"/studio.js\"></script>"))
  check(source.contains("</body>"))
  page.writeText(source.replace("<script src=\"/studio.js\"></script>",
   "<script src=\"/comparison-compat.js\"></script><script src=\"/studio.js\"></script>")
   .replace("</body>", "<script>XOrbitComparison.ready();</script></body>"))
 }
}
tasks.named("preBuild").configure { dependsOn(comparisonAssets) }
