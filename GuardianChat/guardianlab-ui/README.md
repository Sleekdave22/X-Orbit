# GuardianLab Android Protection UI — integration guide

This library puts GuardianLab’s protection warning, false-alarm guidance, temporary override and countdown inside an incorporating Android app. It is a UI integration library, **not a packaged camera/AI detector**. The existing GuardianLab app supplies real detector events; the separate `integration-demo` app supplies explicitly simulated events. The existing `sample` app now uses ProtectionNotice while retaining selective-region masking and real on-device phone detection.

## Requirements and installation

Android API 29+, Java 11-compatible build, AndroidX Lifecycle. The AAR is built against SDK 36.1. Native Android views are supported directly; Compose, Flutter and React Native need their own native view/lifecycle bridge. iOS and unsupported POS hardware are outside this package.

Inside this repository, add `implementation(project(":guardianlab-ui"))`. Outside it, put the release AAR in the host’s `libs/` folder and add:

```kotlin
implementation(files("libs/guardianlab-ui-release.aar"))
implementation("androidx.core:core-ktx:1.10.1")
implementation("androidx.lifecycle:lifecycle-runtime-ktx:2.6.1")
```

For binary AAR consumers, dependencies are declared by the host (an AAR alone does not carry Maven dependency metadata). There is no public Maven publication or camera permission in this UI library.

## Attach to a host screen

Call on the main thread after adding the screen’s content to a `FrameLayout`:

```kotlin
import com.guardianlab.ui.GuardianProtection

val protection = GuardianProtection.attach(rootLayout, this)
protection.protect(balanceView)
protection.protect(transactionDetailsView)

// Invoke on the main thread after your detector confirms a risk:
protection.reportThreat("phone", "Camera device detected")
protection.reportThreat("viewer", "Additional viewer detected")

// Clear each detector independently:
protection.clearThreat("phone", delayMillis = 3000L)
protection.clearThreat("viewer")
```

The lifecycle owner is normally a ComponentActivity or Fragment viewLifecycleOwner. It cancels pauses when the screen stops and automatically closes the UI when destroyed. Call `unprotect(view)` before removing a registered sensitive view. Use `close()` when replacing the screen earlier.

The warning blocks interaction with the underlying screen while shielded. Only registered views are hidden; the full-screen shield also covers the host content in that root. During a pause, a bottom countdown panel remains visible, detection events continue to update, and automatic shielding resumes after 30 seconds if a threat is still active. Clearing a threat during the pause prevents stale re-shielding. The user can resume early.

For host screens where an override must be forbidden:

```kotlin
val protection = GuardianProtection.attach(rootLayout, this, allowTemporaryOverride = false)
```

This hides the pause button and removes the pause suggestion from the guidance. The library opens no camera, sends no data, and adds no system-wide overlay permission. It protects only this host root; dialogs, other windows, screenshots and external capture are not guaranteed to be blocked. A new root or screen needs its own instance. Do not register the root itself.

## Verify an external host

`integration-demo` is a separate application ID with no dependency on the GuardianLab app or its models. It imports this library and demonstrates the same protection UI.

```sh
./gradlew :guardianlab-ui:assembleRelease :guardianlab-ui:testDebugUnitTest
./gradlew :integration-demo:assembleDebug :integration-demo:connectedDebugAndroidTest
```

Outputs: `guardianlab-ui/build/outputs/aar/guardianlab-ui-release.aar` and `integration-demo/build/outputs/apk/debug/integration-demo-debug.apk`.

## Existing selective-protection SDK

The `guardianlab` module retains GuardianDetector, ProtectionController and ProtectedRegion. The `sample` app is the original balance/image/document demo and now displays shared `com.guardianlab.ui.ProtectionNotice` controls. `ProtectionController.pauseProtection(now)` returns an effective decision revealing selected regions for 30 seconds while fresh usable detector frames continue. Missing frames, camera failure, unusable views, lifecycle pause and severe heat cancel the override and keep regions covered. `resumeProtection(now)` ends the override immediately. Set `ProtectionPolicy(allowTemporaryOverride = false)` to forbid it. Render decisions and notice controls on the UI thread.

The original demo currently detects phones, not additional viewers or camera glasses. The original GuardianLab app has additional-viewer detection. The reusable UI accepts either warning from a host; it does not manufacture detections.

For an external host wanting real phone detection, include both `guardianlab-release.aar` and `guardianlab-ui-release.aar`, plus ONNX Runtime Android 1.20.0 and the AndroidX dependencies above. CameraX and camera permission belong to the host camera integration. Consult `guardianlab` source and `sample` for the complete frame evaluator and fail-closed lifecycle flow. Neither binary is a guarantee of accuracy or production certification.
