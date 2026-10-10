package com.guardianlab.app

import kotlin.math.max
import kotlin.math.min

data class GuardianEvidenceSnapshot(
    val hasCandidate: Boolean,
    val confidence: Float,
    val widthRatio: Float,
    val heightRatio: Float,
    val areaRatio: Float,
    val aspectRatio: Float,
    val iouWithPrevious: Float,
    val persistenceFrames: Int
)

class GuardianEvidenceEngine {

    private var previousCandidate: DetectionResult? = null
    private var persistenceFrames = 0

    fun update(
        proposals: List<DetectionResult>,
        frameWidth: Int,
        frameHeight: Int
    ): GuardianEvidenceSnapshot {

        if (frameWidth <= 0 || frameHeight <= 0) {
            reset()
            return emptySnapshot()
        }

        /*
         * For shadow evidence only:
         * consider substantial proposals so the very narrow padding-edge
         * artifacts do not dominate the temporal evidence stream.
         *
         * This does NOT affect YOLO detections or Guardian protection.
         */
        val candidate = proposals
            .filter {
                (it.x2 - it.x1) >= 50f &&
                (it.y2 - it.y1) >= 50f
            }
            .maxByOrNull { it.confidence }

        if (candidate == null) {
            reset()
            return emptySnapshot()
        }

        val boxWidth = candidate.x2 - candidate.x1
        val boxHeight = candidate.y2 - candidate.y1

        val widthRatio =
            boxWidth / frameWidth.toFloat()

        val heightRatio =
            boxHeight / frameHeight.toFloat()

        val areaRatio =
            (boxWidth * boxHeight) /
                (frameWidth.toFloat() * frameHeight.toFloat())

        val aspectRatio =
            if (boxHeight > 0f) {
                boxWidth / boxHeight
            } else {
                0f
            }

        val iou =
            previousCandidate?.let {
                calculateIoU(candidate, it)
            } ?: 0f

        /*
         * Persistence is intentionally very simple for the first shadow pass:
         * a candidate is considered continuous when it overlaps the previous
         * substantial candidate by at least 0.30 IoU.
         *
         * This is diagnostic only and will be calibrated from real phone and
         * no-phone runs before it is allowed to affect protection.
         */
        persistenceFrames =
            if (previousCandidate != null && iou >= 0.30f) {
                persistenceFrames + 1
            } else {
                1
            }

        previousCandidate = candidate

        return GuardianEvidenceSnapshot(
            hasCandidate = true,
            confidence = candidate.confidence,
            widthRatio = widthRatio,
            heightRatio = heightRatio,
            areaRatio = areaRatio,
            aspectRatio = aspectRatio,
            iouWithPrevious = iou,
            persistenceFrames = persistenceFrames
        )
    }

    fun reset() {
        previousCandidate = null
        persistenceFrames = 0
    }

    private fun emptySnapshot(): GuardianEvidenceSnapshot {
        return GuardianEvidenceSnapshot(
            hasCandidate = false,
            confidence = 0f,
            widthRatio = 0f,
            heightRatio = 0f,
            areaRatio = 0f,
            aspectRatio = 0f,
            iouWithPrevious = 0f,
            persistenceFrames = 0
        )
    }

    private fun calculateIoU(
        a: DetectionResult,
        b: DetectionResult
    ): Float {

        val intersectionX1 = max(a.x1, b.x1)
        val intersectionY1 = max(a.y1, b.y1)
        val intersectionX2 = min(a.x2, b.x2)
        val intersectionY2 = min(a.y2, b.y2)

        val intersectionWidth =
            max(0f, intersectionX2 - intersectionX1)

        val intersectionHeight =
            max(0f, intersectionY2 - intersectionY1)

        val intersectionArea =
            intersectionWidth * intersectionHeight

        val areaA =
            max(0f, a.x2 - a.x1) *
                max(0f, a.y2 - a.y1)

        val areaB =
            max(0f, b.x2 - b.x1) *
                max(0f, b.y2 - b.y1)

        val unionArea =
            areaA + areaB - intersectionArea

        return if (unionArea > 0f) {
            intersectionArea / unionArea
        } else {
            0f
        }
    }
}
