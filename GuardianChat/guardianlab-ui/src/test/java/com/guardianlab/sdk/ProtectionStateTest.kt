package com.guardianlab.ui

import org.junit.Assert.*
import org.junit.Test

class ProtectionStateTest {
    @Test fun pauseExpiresAndRestoresExistingThreat() {
        var now = 100L
        val state = ProtectionState({ now }, true)
        state.report("phone", "Phone detected")
        state.pause()
        assertFalse(state.protected)
        assertEquals(30L, state.remainingSeconds)
        now += 29_999
        assertTrue(state.paused)
        now++
        assertTrue(state.protected)
    }
    @Test fun clearedThreatDoesNotReturnAfterPause() {
        var now = 100L
        val state = ProtectionState({ now }, true)
        state.report("phone", "Phone detected"); state.pause(); state.clear("phone")
        now += 30_000
        assertFalse(state.protected)
    }
    @Test fun oneSourceCannotClearAnother() {
        val state = ProtectionState({ 100L }, true)
        state.report("phone", "Phone detected"); state.report("face", "Viewer detected")
        state.clear("face")
        assertTrue(state.protected)
        assertEquals("Phone detected", state.message)
    }
    @Test fun hostCanDisableOverrides() {
        val state = ProtectionState({ 100L }, false)
        state.report("phone", "Phone detected"); state.pause()
        assertFalse(state.paused)
        assertTrue(state.protected)
    }
    @Test fun resumeUsesCurrentThreat() {
        val state = ProtectionState({ 100L }, true)
        state.report("phone", "Phone detected"); state.pause()
        state.report("face", "Viewer detected"); state.resume()
        assertTrue(state.protected)
        assertEquals("Viewer detected", state.message)
    }
}
