package com.guardianlab.app

import org.junit.Assert.*
import org.junit.Test

class ProtectionOverrideTest {
    @Test fun expiresAtThirtySeconds() {
        var now = 100L
        val state = ProtectionOverride { now }
        assertFalse(state.isPaused())
        state.pause()
        assertEquals(30L, state.remainingSeconds())
        now += 29_999L
        assertTrue(state.isPaused())
        assertEquals(1L, state.remainingSeconds())
        now += 1L
        assertFalse(state.isPaused())
        assertEquals(0L, state.remainingSeconds())
    }
    @Test fun resumeEndsPauseImmediately() {
        val state = ProtectionOverride { 100L }
        state.pause()
        state.resume()
        assertFalse(state.isPaused())
    }
}
