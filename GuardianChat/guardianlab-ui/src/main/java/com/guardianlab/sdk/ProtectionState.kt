package com.guardianlab.ui

internal class ProtectionState(private val now: () -> Long, val allowOverride: Boolean) {
    private val threats = linkedMapOf<String, String>()
    private var deadline = 0L
    val message: String? get() = threats.values.lastOrNull()
    val remainingSeconds: Long get() = ((deadline - now()).coerceAtLeast(0L) + 999L) / 1000L
    val paused: Boolean get() = remainingSeconds > 0L
    val protected: Boolean get() = message != null && !paused
    fun report(source: String, message: String) {
        require(source.isNotBlank() && message.isNotBlank())
        threats[source] = message
    }
    fun clear(source: String) { threats.remove(source) }
    fun clearAll() { threats.clear() }
    fun pause() { if (allowOverride && message != null) deadline = now() + 30_000L }
    fun resume() { deadline = 0L }
}
