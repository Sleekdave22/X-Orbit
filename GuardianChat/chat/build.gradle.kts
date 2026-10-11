plugins { alias(libs.plugins.android.application) }
android {
 namespace = "com.guardianlab.chat"
 compileSdk { version = release(36) { minorApiLevel = 1 } }
 defaultConfig { applicationId = "com.guardianlab.chat"; minSdk = 29; targetSdk = 36; versionCode = 2; versionName = "0.2-view-once"; ndk { abiFilters += "arm64-v8a" } }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies {
 implementation(project(":guardianlab"))
 implementation(project(":guardianlab-ui"))
 implementation("androidx.activity:activity-ktx:1.8.0")
 implementation("androidx.camera:camera-camera2:1.6.1")
 implementation("androidx.camera:camera-lifecycle:1.6.1")
 implementation("com.google.mlkit:face-detection:16.1.7")
}
