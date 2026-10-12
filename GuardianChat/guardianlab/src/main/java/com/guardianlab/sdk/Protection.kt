package com.guardianlab.sdk

/** Monotonic milliseconds, normally SystemClock.elapsedRealtime(). */
data class ProtectionPolicy(
 val threshold: Float = 0.50f,
 val confirmationFrames: Int = 3,
 val windowFrames: Int = 5,
 val clearMillis: Long = 3000,
 val staleMillis: Long = 2000,
 val manualResume: Boolean = false,
 val coverOnCandidate: Boolean = true,
 val initialClearMillis: Long = clearMillis,
 val allowTemporaryOverride: Boolean = false
) {
 init { require(threshold in 0f..1f); require(confirmationFrames in 1..windowFrames); require(clearMillis > 0 && staleMillis > 0 && initialClearMillis > 0) }
}
enum class ProtectionState { INITIALIZING, WAITING_FOR_CLEAR, CLEAR, POSSIBLE_DEVICE, DEVICE_CONFIRMED, READY_TO_RESUME, CAMERA_VIEW_UNAVAILABLE, MONITORING_UNAVAILABLE }
data class ProtectionDecision(val state: ProtectionState, val coverContent: Boolean, val pauseRemainingSeconds: Long = 0L)

/** One instance per protected-content session. Call from one thread. */
class ProtectionController(val policy: ProtectionPolicy = ProtectionPolicy()) {
 private var pauseUntil = 0L
 private val history = ArrayDeque<Boolean>()
 private var lastFrame: Long? = null
 private var clearSince: Long? = null
 private var startup = true
 private var latched = false
 private var decision = ProtectionDecision(ProtectionState.INITIALIZING, true)
 fun reset(): ProtectionDecision {
  pauseUntil = 0L
  startup = true
  history.clear(); lastFrame = null; clearSince = null; latched = false
  decision = ProtectionDecision(ProtectionState.INITIALIZING, true); return decision
 }
 fun unavailable(): ProtectionDecision {
  startup = false
  pauseUntil = 0L
  history.clear(); lastFrame = null; clearSince = null; latched = true
  decision = ProtectionDecision(ProtectionState.MONITORING_UNAVAILABLE, true); return decision
 }
 /** An arriving frame with an unusable view must never count as a clear frame. */
 fun cameraViewUnavailable(now: Long): ProtectionDecision {
  startup = false
  pauseUntil = 0L
  history.clear(); lastFrame = now; clearSince = null; latched = true
  decision = ProtectionDecision(ProtectionState.CAMERA_VIEW_UNAVAILABLE, true); return decision
 }
 fun tick(now: Long): ProtectionDecision {
  val last = lastFrame
  if (last != null && now - last >= policy.staleMillis) return unavailable()
  return effective(now)
 }
 fun frame(devicePresent: Boolean, now: Long): ProtectionDecision {
  val last = lastFrame
  if (last != null && now - last >= policy.staleMillis) unavailable()
  lastFrame = now
  history.addLast(devicePresent)
  while (history.size > policy.windowFrames) history.removeFirst()
  if (devicePresent) startup = false
  if (devicePresent) clearSince = null else if (clearSince == null) clearSince = now
  if (devicePresent && history.count { it } >= policy.confirmationFrames) latched = true
  val cleared = clearSince?.let { now - it >= if(startup)policy.initialClearMillis else policy.clearMillis } ?: false
  decision = when {
   latched && cleared && policy.manualResume -> ProtectionDecision(ProtectionState.READY_TO_RESUME, true)
   latched && cleared -> { latched = false; history.clear(); ProtectionDecision(ProtectionState.CLEAR, false) }
   latched -> ProtectionDecision(ProtectionState.DEVICE_CONFIRMED, true)
   devicePresent -> ProtectionDecision(ProtectionState.POSSIBLE_DEVICE, policy.coverOnCandidate || decision.coverContent)
   cleared -> ProtectionDecision(ProtectionState.CLEAR, false)
   decision.coverContent -> ProtectionDecision(ProtectionState.WAITING_FOR_CLEAR, true)
   else -> ProtectionDecision(ProtectionState.CLEAR, false)
  }
  if(decision.state==ProtectionState.CLEAR)startup=false
  return effective(now)
 }
 /** Keep protection latched while discarding votes from a previous qualification threshold. */
 fun resetConfirmationHistory() { history.clear() }
 private fun effective(now: Long): ProtectionDecision {
  val seconds = ((pauseUntil-now).coerceAtLeast(0L)+999L)/1000L
  return if(seconds>0L)decision.copy(coverContent=false,pauseRemainingSeconds=seconds) else decision
 }
 fun pauseProtection(now: Long): ProtectionDecision {
  tick(now)
  if(policy.allowTemporaryOverride && decision.coverContent && decision.state in setOf(
   ProtectionState.POSSIBLE_DEVICE, ProtectionState.DEVICE_CONFIRMED,
   ProtectionState.WAITING_FOR_CLEAR, ProtectionState.READY_TO_RESUME
  )) pauseUntil=now+30_000L
  return effective(now)
 }
 fun resumeProtection(now: Long): ProtectionDecision { pauseUntil=0L;return tick(now) }
 fun resume(now: Long): ProtectionDecision {
  tick(now)
  if (decision.state == ProtectionState.READY_TO_RESUME) {
   latched = false; history.clear(); decision = ProtectionDecision(ProtectionState.CLEAR, false)
  }
  return decision
 }
}
