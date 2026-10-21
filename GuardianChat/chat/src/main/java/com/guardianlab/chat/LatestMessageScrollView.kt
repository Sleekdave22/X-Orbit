package com.guardianlab.chat

import android.content.Context
import android.view.MotionEvent
import android.view.ViewConfiguration
import android.view.View
import android.view.ViewTreeObserver
import android.graphics.Rect
import android.widget.ScrollView
import kotlin.math.abs

/** Anchor after layout, including late media sizing, until the reader scrolls up. */
internal class LatestMessageScrollView(context: Context) : ScrollView(context) {
    private var followingLatest = true
    private var revealPending = false
    private var downY = 0f
    private var downX = 0f
    private var userTouch = false
    private var positioning = false
    private val slop = ViewConfiguration.get(context).scaledTouchSlop
    private fun bottomOffset() = latestOffset(getChildAt(0)?.height ?: 0, height, paddingTop, paddingBottom)
    private val beforeDraw = ViewTreeObserver.OnPreDrawListener {
        // Android may restore descendant focus after onLayout. Position at the
        // final drawing boundary, and never interpret that focus scroll as a drag.
        if (followingLatest) {
            positioning = true
            scrollTo(0, bottomOffset())
            positioning = false
        }
        if (revealPending && !isLayoutRequested && getChildAt(0)?.isLayoutRequested != true) {
            alpha = 1f
            revealPending = false
            if (BuildConfig.DEBUG) try {
                java.io.File(context.filesDir,"chat-position-diagnostic.json").writeText(
                    "{\"content\":"+(getChildAt(0)?.height ?: 0)+",\"viewport\":"+height+",\"scroll\":"+scrollY+",\"bottom\":"+bottomOffset()+"}")
            } catch (_: Exception) {}
        }
        true
    }

    override fun onAttachedToWindow() {
        super.onAttachedToWindow()
        viewTreeObserver.addOnPreDrawListener(beforeDraw)
    }

    override fun onDetachedFromWindow() {
        if (viewTreeObserver.isAlive) viewTreeObserver.removeOnPreDrawListener(beforeDraw)
        super.onDetachedFromWindow()
    }

    fun revealLatest() {
        followingLatest = true
        revealPending = true
        requestLayout()
        invalidate()
    }

    override fun onLayout(changed: Boolean, left: Int, top: Int, right: Int, bottom: Int) {
        val anchor = followingLatest
        positioning = true
        super.onLayout(changed, left, top, right, bottom)
        if (anchor) {
            scrollTo(0, latestOffset(getChildAt(0)?.height ?: 0, height, paddingTop, paddingBottom))
        }
        positioning = false
    }

    override fun onInterceptTouchEvent(event: MotionEvent): Boolean {
        when (event.actionMasked) {
            MotionEvent.ACTION_DOWN -> { downY = event.y; downX = event.x; userTouch = true }
            MotionEvent.ACTION_MOVE -> if (abs(event.y - downY) > slop && abs(event.y-downY) > abs(event.x-downX)) followingLatest = false
        }
        return super.onInterceptTouchEvent(event)
    }

    override fun onScrollChanged(left: Int, top: Int, oldLeft: Int, oldTop: Int) {
        super.onScrollChanged(left, top, oldLeft, oldTop)
        if (!positioning && userTouch) followingLatest =
            latestOffset(getChildAt(0)?.height ?: 0, height, paddingTop, paddingBottom) - top <= slop
    }

    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.actionMasked == MotionEvent.ACTION_DOWN) userTouch = true
        val result = super.onTouchEvent(event)
        if (event.actionMasked == MotionEvent.ACTION_UP || event.actionMasked == MotionEvent.ACTION_CANCEL) userTouch = false
        return result
    }

    override fun requestChildRectangleOnScreen(child: View, rectangle: Rect, immediate: Boolean): Boolean =
        if (followingLatest) false else super.requestChildRectangleOnScreen(child, rectangle, immediate)

    companion object {
        internal fun latestOffset(contentHeight: Int, viewportHeight: Int, topPadding: Int, bottomPadding: Int) =
            maxOf(0, contentHeight - maxOf(0, viewportHeight - topPadding - bottomPadding))
    }
}
