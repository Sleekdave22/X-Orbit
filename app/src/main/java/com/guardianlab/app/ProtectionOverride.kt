package com.guardianlab.app

/** Uses a monotonic clock so wall-clock changes cannot extend an override. */
class ProtectionOverride(private val now: () -> Long) {
    private var deadline = 0L
    fun pause() { deadline = now() + 30_000L }
    fun resume() { deadline = 0L }
    fun remainingSeconds(): Long = ((deadline - now()).coerceAtLeast(0L) + 999L) / 1000L
    fun isPaused(): Boolean = remainingSeconds() > 0L
}
