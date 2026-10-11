package com.guardianlab.ui

import android.content.Context
import android.graphics.Color
import android.view.View
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView

/** Shared guidance and override controls for hosts using selective ProtectedRegion masks. */
class ProtectionNotice(context: Context) : LinearLayout(context) {
    var onPause: (() -> Unit)? = null
    var onResume: (() -> Unit)? = null
    private var paused = false
    private val note = TextView(context).apply {
        textSize = 14f
        setTextColor(Color.rgb(83,100,116))
    }
    private val action = Button(context).apply {
        isAllCaps = false
        setOnClickListener { if (paused) onResume?.invoke() else onPause?.invoke() }
    }
    init { orientation = VERTICAL; addView(note); addView(action); visibility = GONE }
    fun render(covered: Boolean, remainingSeconds: Long = 0L, allowOverride: Boolean = false) {
        paused = remainingSeconds > 0L
        visibility = if (covered || paused) VISIBLE else GONE
        note.text = if (paused) context.getString(R.string.guardianlab_paused, remainingSeconds)
            else context.getString(if (allowOverride) R.string.guardianlab_guidance else R.string.guardianlab_guidance_no_override)
        action.visibility = if (allowOverride) VISIBLE else GONE
        action.setText(if (paused) R.string.guardianlab_resume else R.string.guardianlab_show_screen)
    }
}
