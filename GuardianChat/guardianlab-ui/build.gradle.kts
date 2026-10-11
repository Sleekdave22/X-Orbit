group = "com.guardianlab"
version = "0.7.0-controls"
plugins { alias(libs.plugins.android.library) }
android {
    namespace = "com.guardianlab.ui"
    compileSdk { version = release(36) { minorApiLevel = 1 } }
    defaultConfig { minSdk = 29 }
    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }
}
dependencies {
    implementation(libs.androidx.core.ktx)
    api(libs.androidx.lifecycle.runtime.ktx)
    testImplementation(libs.junit)
}
