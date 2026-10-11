package com.guardianlab.ui

import android.graphics.Color
import android.os.Handler
import android.os.Looper
import android.os.SystemClock
import android.view.Gravity
import android.view.View
import android.widget.*
import androidx.core.view.ViewCompat
import androidx.core.view.WindowInsetsCompat
import androidx.lifecycle.DefaultLifecycleObserver
import androidx.lifecycle.LifecycleOwner

/** In-app protection UI. The host supplies confirmed detector events; no camera is started. */
class GuardianProtection private constructor(
    private val root: FrameLayout,
    private val owner: LifecycleOwner,
    allowOverride: Boolean
) : DefaultLifecycleObserver, AutoCloseable {
    private val handler = Handler(Looper.getMainLooper())
    private val state = ProtectionState({ SystemClock.elapsedRealtime() }, allowOverride)
    private val targets = linkedMapOf<View, Int>()
    private var closed = false
    private val panel = LinearLayout(root.context).apply {
        orientation = LinearLayout.VERTICAL
        gravity = Gravity.CENTER
        setPadding(dp(20), dp(20), dp(20), dp(20))
        setBackgroundColor(Color.BLACK)
        isClickable = true
        visibility = View.GONE
    }
    private val title = TextView(root.context).apply {
        setTextColor(Color.WHITE); textSize = 20f; gravity = Gravity.CENTER
        accessibilityLiveRegion = View.ACCESSIBILITY_LIVE_REGION_POLITE
    }
    private val guidance = TextView(root.context).apply {
        setTextColor(Color.WHITE); textSize = 16f; gravity = Gravity.CENTER
        setPadding(0, dp(16), 0, dp(16))
        setText(if (allowOverride) R.string.guardianlab_guidance else R.string.guardianlab_guidance_no_override)
    }
    private val button = Button(root.context)
    private val tick = object : Runnable {
        override fun run() {
            if (closed) return
            render()
            if (state.paused) handler.postDelayed(this, 250L)
        }
    }
    private val clearTasks = mutableMapOf<String, Runnable>()

    init {
        checkMainThread()
        panel.addView(title)
        panel.addView(guidance)
        panel.addView(button)
        root.addView(panel, FrameLayout.LayoutParams(-1, -1))
        ViewCompat.setOnApplyWindowInsetsListener(panel) { view, insets ->
            val bars = insets.getInsets(WindowInsetsCompat.Type.systemBars())
            view.setPadding(dp(20) + bars.left, dp(20) + bars.top, dp(20) + bars.right, dp(20) + bars.bottom)
            insets
        }
        button.setOnClickListener {
            if (state.paused) resumeProtection() else pauseProtection()
        }
        owner.lifecycle.addObserver(this)
        ViewCompat.requestApplyInsets(panel)
    }

    /** Register only visible sensitive views belonging to this screen. */
    fun protect(view: View) {
        checkOpen()
        require(view !== root && view !== panel) { "Protect a sensitive child view, not the root." }
        require(generateSequence(view.parent) { it.parent }.any { it === root }) {
            "The protected view must belong to the attached root."
        }
        if (!targets.containsKey(view)) targets[view] = view.visibility
        render()
    }

    fun unprotect(view: View) {
        checkOpen()
        targets.remove(view)?.let { view.visibility = it }
        render()
    }

    /** Independent sources prevent a clear face result from clearing a phone threat. */
    fun reportThreat(source: String, message: String) {
        checkOpen()
        clearTasks.remove(source)?.let { handler.removeCallbacks(it) }
        state.report(source, message)
        render()
    }

    fun clearThreat(source: String, delayMillis: Long = 0L) {
        checkOpen()
        require(delayMillis >= 0)
        if (clearTasks.containsKey(source)) return
        if (delayMillis == 0L) {
            state.clear(source); render()
        } else {
            val task = Runnable { clearTasks.remove(source); state.clear(source); render() }
            clearTasks[source] = task
            handler.postDelayed(task, delayMillis)
        }
    }

    fun clearThreats() {
        checkOpen()
        clearTasks.values.forEach { handler.removeCallbacks(it) }
        clearTasks.clear()
        state.clearAll()
        render()
    }

    fun pauseProtection() {
        checkOpen()
        state.pause()
        handler.removeCallbacks(tick)
        render()
        if (state.paused) handler.postDelayed(tick, 250L)
    }

    fun resumeProtection() {
        checkOpen()
        state.resume()
        handler.removeCallbacks(tick)
        render()
    }

    private fun render() {
        targets.forEach { (view, original) ->
            view.visibility = if (state.protected) View.INVISIBLE else original
        }
        val show = targets.isNotEmpty() && (state.protected || state.paused)
        panel.visibility = if (show) View.VISIBLE else View.GONE
        if (!show) return
        val params = panel.layoutParams as FrameLayout.LayoutParams
        params.height = if (state.paused) FrameLayout.LayoutParams.WRAP_CONTENT else FrameLayout.LayoutParams.MATCH_PARENT
        params.gravity = Gravity.BOTTOM
        panel.layoutParams = params
        title.text = if (state.paused) root.context.getString(R.string.guardianlab_paused, state.remainingSeconds)
            else state.message ?: root.context.getString(R.string.guardianlab_protected)
        guidance.visibility = if (state.paused) View.GONE else View.VISIBLE
        button.visibility = if (state.allowOverride) View.VISIBLE else View.GONE
        button.setText(if (state.paused) R.string.guardianlab_resume else R.string.guardianlab_show_screen)
        panel.bringToFront()
    }

    override fun onStop(owner: LifecycleOwner) { if (!closed) resumeProtection() }
    override fun onDestroy(owner: LifecycleOwner) { close() }
    override fun close() {
        checkMainThread()
        if (closed) return
        handler.removeCallbacksAndMessages(null)
        clearTasks.clear()
        targets.forEach { (view, original) -> view.visibility = original }
        targets.clear()
        root.removeView(panel)
        owner.lifecycle.removeObserver(this)
        closed = true
    }
    private fun dp(value: Int) = (value * root.resources.displayMetrics.density).toInt()
    private fun checkOpen() { checkMainThread(); check(!closed) { "Protection is closed." } }
    private fun checkMainThread() { check(Looper.myLooper() == Looper.getMainLooper()) { "Use the main thread." } }

    companion object {
        /** Attach once per screen, after adding host views to the root. */
        @JvmStatic
        @JvmOverloads
        fun attach(root: FrameLayout, lifecycleOwner: LifecycleOwner, allowTemporaryOverride: Boolean = false): GuardianProtection =
            GuardianProtection(root, lifecycleOwner, allowTemporaryOverride)
    }
}
