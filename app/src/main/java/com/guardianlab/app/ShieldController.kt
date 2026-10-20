package com.guardianlab.app

import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.widget.Button
import android.widget.LinearLayout
import android.view.Gravity
import android.view.View
import android.widget.FrameLayout
import android.widget.TextView

class ShieldController(
    private val shieldView: View,
    private val blurPanel: View,
    private val warningText: TextView,
    private val rootLayout: FrameLayout
) {

    private val handler = Handler(Looper.getMainLooper())

    private val protectionTargets = mutableListOf<ProtectionTarget>()

    private val pauseState = ProtectionOverride { SystemClock.elapsedRealtime() }
    private var latestThreat: String? = null
    private val pauseStatus = TextView(rootLayout.context).apply {
        setTextColor(Color.WHITE)
        textSize = 16f
        gravity = Gravity.CENTER
    }
    private val falseAlarmNote = TextView(rootLayout.context).apply {
        setText(R.string.protection_false_alarm_guidance)
        setTextColor(Color.WHITE)
        textSize = 14f
        gravity = Gravity.CENTER
        maxWidth = (320 * rootLayout.resources.displayMetrics.density).toInt()
        val padding = (12 * rootLayout.resources.displayMetrics.density).toInt()
        setPadding(padding, padding, padding, padding)
    }
    private val overrideButton = Button(rootLayout.context).apply {
        setBackgroundColor(Color.parseColor("#e8b84a")); setTextColor(Color.parseColor("#1b0709"))
    }
    private val controls = LinearLayout(rootLayout.context).apply {
        orientation = LinearLayout.VERTICAL
        setBackgroundColor(Color.parseColor("#1b0709"))
        setPadding(16, 8, 16, 8)
        addView(falseAlarmNote)
        addView(pauseStatus)
        addView(overrideButton)
        visibility = View.GONE
    }
    private val tick = object : Runnable {
        override fun run() {
            if (pauseState.isPaused()) {
                updateControls()
                handler.postDelayed(this, 250L)
            } else {
                resumeProtection()
            }
        }
    }

    init {
        rootLayout.addView(controls, FrameLayout.LayoutParams(
            FrameLayout.LayoutParams.WRAP_CONTENT,
            FrameLayout.LayoutParams.WRAP_CONTENT
        ).apply {
            gravity = Gravity.BOTTOM or Gravity.CENTER_HORIZONTAL
            bottomMargin = (100 * rootLayout.resources.displayMetrics.density).toInt()
        })
        androidx.core.view.ViewCompat.setOnApplyWindowInsetsListener(controls) { view, insets ->
            val params = view.layoutParams as FrameLayout.LayoutParams
            params.bottomMargin = insets.getInsets(
                androidx.core.view.WindowInsetsCompat.Type.navigationBars()
            ).bottom + (100 * rootLayout.resources.displayMetrics.density).toInt()
            view.layoutParams = params
            insets
        }
        overrideButton.setOnClickListener {
            if (pauseState.isPaused()) resumeProtection() else pauseProtection()
        }
    }

    private fun updateControls() {
        val paused = pauseState.isPaused()
        controls.visibility = if (paused || latestThreat != null) View.VISIBLE else View.GONE
        falseAlarmNote.visibility = if (paused) View.GONE else View.VISIBLE
        pauseStatus.text = if (paused) "Protection paused · ${pauseState.remainingSeconds()}s remaining" else ""
        pauseStatus.visibility = if (paused) View.VISIBLE else View.GONE
        overrideButton.text = if (paused) "Resume protection" else "Show screen for 30 seconds"
        controls.bringToFront()
    }

    private fun pauseProtection() {
        pauseState.pause()
        handler.removeCallbacks(hideRunnable)
        hideScheduled = false
        hideRunnable.run()
        warningText.animate().setListener(null).cancel()
        warningText.visibility = View.GONE
        updateControls()
        handler.removeCallbacks(tick)
        handler.post(tick)
    }

    private fun resumeProtection() {
        pauseState.resume()
        handler.removeCallbacks(tick)
        latestThreat?.let { showProtection(it) } ?: updateControls()
    }

    fun dispose() {
        handler.removeCallbacksAndMessages(null)
    }

    private var hideScheduled = false

    private val hideRunnable = Runnable {

        hideScheduled = false

        shieldView.visibility = View.GONE
        blurPanel.visibility = View.GONE
        warningText.text = ""

        updateControls()

        protectionTargets.forEach { target ->

            target.view.visibility = View.VISIBLE

            target.protectionOverlay?.let {
                rootLayout.removeView(it)
            }

            target.protectionOverlay = null
        }
    }

    fun addProtectionTarget(target: ProtectionTarget) {
        protectionTargets.add(target)
    }

    fun removeProtectionTarget(target: ProtectionTarget) {
        protectionTargets.remove(target)
    }

    fun showProtection(message: String) {
        latestThreat = message
        if (pauseState.isPaused()) {
            warningText.animate().setListener(null).cancel()
            warningText.visibility = View.GONE
            updateControls()
            return
        }
        updateControls()
        warningText.animate().setListener(null).cancel()
        warningText.visibility = View.VISIBLE
        warningText.translationY = 0f


        handler.removeCallbacks(hideRunnable)
        hideScheduled = false

        warningText.text = message

        shieldView.visibility = View.GONE
        blurPanel.visibility = View.GONE

        protectionTargets.forEach { target ->

            target.view.visibility = View.INVISIBLE

            // Prevent duplicate protection overlays
            if (target.protectionOverlay != null) {
                return@forEach
            }

            val location = IntArray(2)
            target.view.getLocationInWindow(location)

            val rootLocation = IntArray(2)
            rootLayout.getLocationInWindow(rootLocation)

            val overlay = TextView(target.view.context).apply {
                text = "🔒 PROTECTED"
                textSize = 18f
                setTextColor(Color.parseColor("#e8b84a"))
                setBackgroundColor(Color.parseColor("#1b0709"))
                gravity = Gravity.CENTER
            }

            val params = FrameLayout.LayoutParams(
                target.view.width,
                target.view.height
            ).apply {
                leftMargin = location[0] - rootLocation[0]
                topMargin = location[1] - rootLocation[1]
            }

            rootLayout.addView(overlay, params)

            target.protectionOverlay = overlay
            controls.bringToFront()
        }
    }

    fun hideProtectionWithDelay(delayMillis: Long = 3000) {
        latestThreat = null
        if (pauseState.isPaused()) {
            updateControls()
            return
        }


        if (
            protectionTargets.any {
                it.view.visibility == View.INVISIBLE
            } && !hideScheduled
        ) {
            hideScheduled = true
            handler.postDelayed(hideRunnable, delayMillis)
        }
    }

    fun clearImmediately() {
        latestThreat = null

        handler.removeCallbacks(hideRunnable)
        hideScheduled = false
        hideRunnable.run()
    }
}