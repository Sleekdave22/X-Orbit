plugins { alias(libs.plugins.android.library); id("maven-publish") }
android {
 namespace = "com.guardianlab.sdk"
 publishing { singleVariant("release") { withSourcesJar() } }
 compileSdk { version = release(36) { minorApiLevel = 1 } }
 defaultConfig { minSdk = 29; consumerProguardFiles("consumer-rules.pro") }
 compileOptions { sourceCompatibility = JavaVersion.VERSION_11; targetCompatibility = JavaVersion.VERSION_11 }
}
dependencies {
 api(project(":guardianlab-ui"))
 implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
 testImplementation("junit:junit:4.13.2")
}

afterEvaluate {
 publishing {
  publications {
   create<MavenPublication>("release") {
    from(components["release"])
    groupId = "com.guardianlab"
    artifactId = "guardianlab-android"
    version = "0.7.0-controls"
    pom { name.set("GuardianLab Android SDK"); description.set("Local phone detection and selective sensitive-region protection pilot") }
   }
  }
  repositories { maven { name = "Pilot"; url = uri(rootProject.layout.buildDirectory.dir("pilot-repository")) } }
 }
}
