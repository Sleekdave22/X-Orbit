package com.guardianlab.app

import kotlin.math.max

enum class LightIntensity {
    DARK,
    NORMAL,
    UNKNOWN
}

enum class LightColorCast {
    NEUTRAL,
    BLUE,
    RED,
    GREEN,
    UNKNOWN
}

data class LightingState(
    val intensity: LightIntensity,
    val colorCast: LightColorCast,

    val rawBrightness: Double,
    val smoothedBrightness: Double,

    val normalizedR: Double,
    val normalizedG: Double,
    val normalizedB: Double
) {
    val profileKey: String
        get() = "${intensity.name}_${colorCast.name}"
}

class LightingAnalyzer {

    private companion object {

        /*
         * PROVISIONAL LIGHTING CLASSIFICATION PARAMETERS.
         *
         * These do NOT yet control YOLO.
         * They will be calibrated from GuardianLab lighting tests.
         */

        // Exponential smoothing across frames.
        const val EMA_ALPHA = 0.15

        // Intensity hysteresis.
        // Dark must fall to/below this level.
        const val DARK_ENTER_MAX = 75.0

        // Normal must rise to/above this level.
        const val NORMAL_ENTER_MIN = 95.0

        // Color dominance required to ENTER a colored-light state.
        const val COLOR_ENTER_DOMINANCE = 0.08

        // Smaller dominance is enough to STAY in an existing color state.
        const val COLOR_EXIT_DOMINANCE = 0.05

        // Require a candidate lighting state to persist before switching.
        const val SWITCH_CONFIRM_FRAMES = 5
    }

    private var smoothedBrightness: Double? = null
    private var smoothedR: Double? = null
    private var smoothedG: Double? = null
    private var smoothedB: Double? = null

    private var currentIntensity = LightIntensity.UNKNOWN
    private var currentColorCast = LightColorCast.UNKNOWN

    private var pendingIntensity: LightIntensity? = null
    private var pendingIntensityFrames = 0

    private var pendingColorCast: LightColorCast? = null
    private var pendingColorFrames = 0

    fun update(
        avgR: Int,
        avgG: Int,
        avgB: Int,
        brightness: Double
    ): LightingState {

        smoothedBrightness =
            ema(smoothedBrightness, brightness)

        smoothedR =
            ema(smoothedR, avgR.toDouble())

        smoothedG =
            ema(smoothedG, avgG.toDouble())

        smoothedB =
            ema(smoothedB, avgB.toDouble())

        val r = smoothedR ?: avgR.toDouble()
        val g = smoothedG ?: avgG.toDouble()
        val b = smoothedB ?: avgB.toDouble()

        val total = max(1.0, r + g + b)

        val normalizedR = r / total
        val normalizedG = g / total
        val normalizedB = b / total

        val brightnessValue =
            smoothedBrightness ?: brightness

        val intensityCandidate =
            classifyIntensity(brightnessValue)

        currentIntensity =
            confirmIntensity(intensityCandidate)

        val colorCandidate =
            classifyColor(
                normalizedR,
                normalizedG,
                normalizedB
            )

        currentColorCast =
            confirmColor(colorCandidate)

        return LightingState(
            intensity = currentIntensity,
            colorCast = currentColorCast,

            rawBrightness = brightness,
            smoothedBrightness = brightnessValue,

            normalizedR = normalizedR,
            normalizedG = normalizedG,
            normalizedB = normalizedB
        )
    }

    private fun ema(
        previous: Double?,
        current: Double
    ): Double {

        if (previous == null) {
            return current
        }

        return previous +
            EMA_ALPHA * (current - previous)
    }

    private fun classifyIntensity(
        brightness: Double
    ): LightIntensity {

        return when (currentIntensity) {

            LightIntensity.DARK -> {
                if (brightness >= NORMAL_ENTER_MIN) {
                    LightIntensity.NORMAL
                } else {
                    LightIntensity.DARK
                }
            }

            LightIntensity.NORMAL -> {
                if (brightness <= DARK_ENTER_MAX) {
                    LightIntensity.DARK
                } else {
                    LightIntensity.NORMAL
                }
            }

            LightIntensity.UNKNOWN -> {
                when {
                    brightness <= DARK_ENTER_MAX ->
                        LightIntensity.DARK

                    brightness >= NORMAL_ENTER_MIN ->
                        LightIntensity.NORMAL

                    else ->
                        LightIntensity.UNKNOWN
                }
            }
        }
    }

    private fun classifyColor(
        r: Double,
        g: Double,
        b: Double
    ): LightColorCast {

        /*
         * Hysteresis for an already-established color cast.
         */

        when (currentColorCast) {

            LightColorCast.BLUE -> {
                if (
                    b - max(r, g) >=
                    COLOR_EXIT_DOMINANCE
                ) {
                    return LightColorCast.BLUE
                }
            }

            LightColorCast.RED -> {
                if (
                    r - max(g, b) >=
                    COLOR_EXIT_DOMINANCE
                ) {
                    return LightColorCast.RED
                }
            }

            LightColorCast.GREEN -> {
                if (
                    g - max(r, b) >=
                    COLOR_EXIT_DOMINANCE
                ) {
                    return LightColorCast.GREEN
                }
            }

            else -> Unit
        }

        return when {

            b - max(r, g) >=
                COLOR_ENTER_DOMINANCE ->
                LightColorCast.BLUE

            r - max(g, b) >=
                COLOR_ENTER_DOMINANCE ->
                LightColorCast.RED

            g - max(r, b) >=
                COLOR_ENTER_DOMINANCE ->
                LightColorCast.GREEN

            else ->
                LightColorCast.NEUTRAL
        }
    }

    private fun confirmIntensity(
        candidate: LightIntensity
    ): LightIntensity {

        if (candidate == LightIntensity.UNKNOWN) {
            pendingIntensity = null
            pendingIntensityFrames = 0
            return currentIntensity
        }

        if (candidate == currentIntensity) {
            pendingIntensity = null
            pendingIntensityFrames = 0
            return currentIntensity
        }

        if (candidate == pendingIntensity) {
            pendingIntensityFrames++
        } else {
            pendingIntensity = candidate
            pendingIntensityFrames = 1
        }

        if (
            pendingIntensityFrames >=
            SWITCH_CONFIRM_FRAMES
        ) {
            currentIntensity = candidate
            pendingIntensity = null
            pendingIntensityFrames = 0
        }

        return currentIntensity
    }

    private fun confirmColor(
        candidate: LightColorCast
    ): LightColorCast {

        if (candidate == currentColorCast) {
            pendingColorCast = null
            pendingColorFrames = 0
            return currentColorCast
        }

        if (candidate == pendingColorCast) {
            pendingColorFrames++
        } else {
            pendingColorCast = candidate
            pendingColorFrames = 1
        }

        if (
            pendingColorFrames >=
            SWITCH_CONFIRM_FRAMES
        ) {
            currentColorCast = candidate
            pendingColorCast = null
            pendingColorFrames = 0
        }

        return currentColorCast
    }
}
