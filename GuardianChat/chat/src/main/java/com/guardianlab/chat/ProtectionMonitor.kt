package com.guardianlab.chat

import android.Manifest
import android.content.pm.PackageManager
import android.graphics.Bitmap
import android.graphics.Matrix
import android.os.*
import androidx.activity.ComponentActivity
import androidx.camera.core.*
import androidx.camera.lifecycle.ProcessCameraProvider
import com.guardianlab.sdk.*
import com.google.android.gms.tasks.Tasks
import com.google.mlkit.vision.common.InputImage
import com.google.mlkit.vision.face.FaceDetection
import com.google.mlkit.vision.face.FaceDetectorOptions
import java.util.concurrent.Executors
import java.util.concurrent.TimeUnit

/** Foreground-only, phone + additional-face test integration. No glasses or frame retention. */
class ProtectionMonitor(private val host:ComponentActivity,private val changed:(ProtectionDecision,String)->Unit):AutoCloseable {
 private val main=Handler(Looper.getMainLooper())
 private val worker=Executors.newSingleThreadExecutor()
 private val controller=ProtectionController(ProtectionPolicy(initialClearMillis=750L,allowTemporaryOverride=false))
 private var detector:GuardianDetector?=null
 private val faces=FaceDetection.getClient(FaceDetectorOptions.Builder().setPerformanceMode(FaceDetectorOptions.PERFORMANCE_MODE_FAST).build())
 private var provider:ProcessCameraProvider?=null
 @Volatile private var active=false;private var closed=false;@Volatile private var generation=0
 private var startAt=0L;private var lastReason="Monitoring unavailable"
 private val power=host.getSystemService(ComponentActivity.POWER_SERVICE) as PowerManager
 private val thermal=PowerManager.OnThermalStatusChangedListener {if(it>=PowerManager.THERMAL_STATUS_SEVERE)stop("Phone needs to cool. Monitoring unavailable.")}
 private val watch=object:Runnable {override fun run(){if(active){
  val now=SystemClock.elapsedRealtime()
  if(now-startAt>12000 && controller.tick(now).state==ProtectionState.INITIALIZING){stop("Camera did not start. Try monitoring again.");return}
  changed(controller.tick(now),lastReason);main.postDelayed(this,250)
 }}}
 init {power.addThermalStatusListener(host.mainExecutor,thermal);worker.execute {try{if(detector==null)detector=GuardianDetector(host.applicationContext)}catch(_:Exception){}}}
 fun start(){
  if(active || closed)return
  if(host.checkSelfPermission(Manifest.permission.CAMERA)!=PackageManager.PERMISSION_GRANTED){stop("Camera permission required");return}
  if(power.currentThermalStatus>=PowerManager.THERMAL_STATUS_SEVERE){stop("Phone needs to cool. Monitoring unavailable.");return}
  active=true;startAt=SystemClock.elapsedRealtime();val gen=++generation;lastReason="Starting monitoring"
  changed(controller.reset(),lastReason);main.post(watch)
  worker.execute {
   try {
    if(detector==null)detector=GuardianDetector(host.applicationContext)
    main.post {
     if(!active || gen!=generation)return@post
     val future=ProcessCameraProvider.getInstance(host)
     future.addListener({
      try {
       if(!active || gen!=generation)return@addListener
       provider=future.get();val cadence=FrameCadence(3);val view=CameraViewEvaluator();val phone=PhoneFrameEvaluator()
       var previousTimestamp=-1L
       val analysis=ImageAnalysis.Builder().setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST).build()
       analysis.setAnalyzer(worker){image->
        val arrived=SystemClock.elapsedRealtime()
        if(!active || gen!=generation || !cadence.shouldAnalyze(arrived)){image.close();return@setAnalyzer}
        var raw:Bitmap?=null;var upright:Bitmap?=null
        try {
         check(image.imageInfo.timestamp>previousTimestamp){"Capture timestamps stopped"};previousTimestamp=image.imageInfo.timestamp
         raw=image.toBitmap();upright=if(image.imageInfo.rotationDegrees==0)raw else Bitmap.createBitmap(raw,0,0,raw.width,raw.height,Matrix().apply {postRotate(image.imageInfo.rotationDegrees.toFloat())},true)
         val quality=view.evaluate(upright)
         val boxes=if(quality.usable)detector!!.detect(upright) else emptyList()
         val qualification=phone.evaluate(upright,boxes);val found=qualification.phonePresent
         val phoneFinished=SystemClock.elapsedRealtime()
         // A phone risk must mask immediately; do not wait for face inference.
         if(found)main.post {if(active && gen==generation){
          lastReason="Phone detected"
          changed(controller.frame(true,arrived),lastReason)
         }}
         val extra=if(quality.usable){
          val faceCopy=upright.copy(Bitmap.Config.ARGB_8888,false)
          val task=faces.process(InputImage.fromBitmap(faceCopy,0))
          task.addOnCompleteListener {faceCopy.recycle()}
          Tasks.await(task,1500,TimeUnit.MILLISECONDS).size>=2
         } else false
         val completed=SystemClock.elapsedRealtime()
         if(host.applicationInfo.flags and android.content.pm.ApplicationInfo.FLAG_DEBUGGABLE != 0)android.util.Log.d("X ORBITLatency","phone_ms=${phoneFinished-arrived} total_ms=${completed-arrived} phone=$found faces=$extra usable=${quality.usable} threshold=${qualification.confidenceThreshold} boxes=${boxes.size} max_score=${boxes.maxOfOrNull {it.confidence}?:0f}")
         main.post {if(active && gen==generation){
          lastReason=if(extra && found)"Phone and additional faces detected" else if(extra)"Additional faces detected" else if(found)"Phone detected" else "Monitoring active"
          val stale=SystemClock.elapsedRealtime()-arrived>=1500
          changed(if(stale)controller.unavailable() else if(!quality.usable)controller.cameraViewUnavailable(arrived) else if(found)controller.tick(SystemClock.elapsedRealtime()) else controller.frame(extra,arrived),if(stale)"Analysis too slow. Monitoring unavailable." else lastReason)
         }}
        }catch(e:Exception){main.post {if(active && gen==generation)stop("Camera analysis unavailable. Retry monitoring.")}}
        finally{if(upright!==raw)upright?.recycle();raw?.recycle();image.close()}
       }
       provider!!.bindToLifecycle(host,CameraSelector.DEFAULT_FRONT_CAMERA,analysis)
      }catch(e:Exception){if(gen==generation)stop("Front camera unavailable. Retry monitoring.")}
     },host.mainExecutor)
    }
   }catch(e:Exception){main.post {if(gen==generation)stop("Detector unavailable. Retry monitoring.")}}
  }
 }
 fun pause(){changed(controller.pauseProtection(SystemClock.elapsedRealtime()),lastReason)}
 fun resumeProtection(){changed(controller.resumeProtection(SystemClock.elapsedRealtime()),lastReason)}
 fun stop(reason:String="Monitoring paused") {generation++;active=false;main.removeCallbacks(watch);provider?.unbindAll();lastReason=reason;changed(controller.unavailable(),reason)}
 override fun close(){if(closed)return;stop();closed=true;power.removeThermalStatusListener(thermal);worker.execute {detector?.close();faces.close()};worker.shutdown()}
}
