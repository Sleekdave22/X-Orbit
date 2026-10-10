package com.guardianlab.app

import android.content.Context
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

object MobileClipBatch7Probe {

    private const val TAG = "GL_MOBILECLIP_BATCH7"

    private const val MODEL_ASSET =
        "D1_K7W_MOBILECLIP2_S0_VISUAL_FP32_EMBEDDED.onnx"

    private const val INPUT_ASSET =
        "d1_l8i_frame060_top7_input_fp32.bin"

    private const val TEXT_ASSET =
        "d1_l8i_text_features_fp32.bin"

    private const val REFERENCE_ASSET =
        "d1_l8i_onnx_reference_embeddings_fp32.bin"

    private const val BATCH = 7
    private const val CHANNELS = 3
    private const val HEIGHT = 256
    private const val WIDTH = 256

    private const val EMBEDDING_SIZE = 512
    private const val PROMPT_COUNT = 6

    private const val INPUT_FLOATS =
        BATCH * CHANNELS * HEIGHT * WIDTH

    private const val TEXT_FLOATS =
        PROMPT_COUNT * EMBEDDING_SIZE

    private const val REFERENCE_FLOATS =
        BATCH * EMBEDDING_SIZE

    private const val EXPECTED_WINNER_RANK = 7
    private const val MARGIN_REFERENCE = 0.005f

    fun run(context: Context) {

        Log.i(TAG, "============================================================")
        Log.i(TAG, "GUARDIANLAB — D1-L8I")
        Log.i(TAG, "GALAXY S21 MOBILECLIP FP32 BATCH-7 VALIDATION")
        Log.i(TAG, "============================================================")

        val environment =
            OrtEnvironment.getEnvironment()

        var session: OrtSession? = null
        var inputTensor: OnnxTensor? = null

        try {

            // ========================================================
            // 1. LOAD EXACT REFERENCE ASSETS
            // ========================================================

            val inputData = loadFloatAsset(
                context,
                INPUT_ASSET,
                INPUT_FLOATS
            )

            val textFeatures = loadFloatAsset(
                context,
                TEXT_ASSET,
                TEXT_FLOATS
            )

            val referenceEmbeddings = loadFloatAsset(
                context,
                REFERENCE_ASSET,
                REFERENCE_FLOATS
            )

            Log.i(TAG, "----------------------------------------------")
            Log.i(TAG, "ASSET VALIDATION")
            Log.i(TAG, "----------------------------------------------")

            Log.i(
                TAG,
                "Input floats     : ${inputData.size}"
            )

            Log.i(
                TAG,
                "Text floats      : ${textFeatures.size}"
            )

            Log.i(
                TAG,
                "Reference floats : ${referenceEmbeddings.size}"
            )

            require(inputData.all { it.isFinite() }) {
                "Input contains non-finite values"
            }

            require(textFeatures.all { it.isFinite() }) {
                "Text features contain non-finite values"
            }

            require(referenceEmbeddings.all { it.isFinite() }) {
                "Reference embeddings contain non-finite values"
            }

            Log.i(TAG, "Reference assets: PASS")

            // ========================================================
            // 2. LOAD EXACT FP32 MOBILECLIP MODEL
            // ========================================================

            val modelBytes =
                context.assets
                    .open(MODEL_ASSET)
                    .use { it.readBytes() }

            Log.i(
                TAG,
                "Model bytes: ${modelBytes.size}"
            )

            val options =
                OrtSession.SessionOptions().apply {

                    // IMPORTANT:
                    // Controlled CPU-only execution.
                    // Do NOT enable NNAPI here.

                    setIntraOpNumThreads(2)

                    setOptimizationLevel(
                        OrtSession.SessionOptions
                            .OptLevel.ALL_OPT
                    )
                }

            val sessionLoadStart =
                System.nanoTime()

            session =
                environment.createSession(
                    modelBytes,
                    options
                )

            val sessionLoadMs =
                (
                    System.nanoTime()
                        - sessionLoadStart
                ) / 1_000_000.0

            Log.i(
                TAG,
                "ORT session load PASS | %.2f ms"
                    .format(
                        java.util.Locale.US,
                        sessionLoadMs
                    )
            )

            // ========================================================
            // 3. CREATE EXACT [BATCH,3,256,256] TENSOR
            // ========================================================

            val inputShape =
                longArrayOf(
                    BATCH.toLong(),
                    CHANNELS.toLong(),
                    HEIGHT.toLong(),
                    WIDTH.toLong()
                )

            inputTensor =
                OnnxTensor.createTensor(
                    environment,
                    FloatBuffer.wrap(inputData),
                    inputShape
                )

            Log.i(
                TAG,
                "Input tensor PASS | shape=[7,3,256,256]"
            )

            // ========================================================
            // 4. WARM-UP
            // ========================================================

            val warmupStart =
                System.nanoTime()

            session.run(
                mapOf(
                    "image" to inputTensor
                )
            ).use {
                // Warm-up only.
            }

            val warmupMs =
                (
                    System.nanoTime()
                        - warmupStart
                ) / 1_000_000.0

            Log.i(
                TAG,
                "Warm-up PASS | %.2f ms"
                    .format(
                        java.util.Locale.US,
                        warmupMs
                    )
            )

            // ========================================================
            // 5. THREE MEASURED BATCH-7 RUNS
            // ========================================================

            val inferenceTimes =
                DoubleArray(3)

            var finalEmbeddings:
                Array<FloatArray>? = null

            for (runIndex in 0 until 3) {

                val startNs =
                    System.nanoTime()

                session.run(
                    mapOf(
                        "image" to inputTensor
                    )
                ).use { result ->

                    val elapsedMs =
                        (
                            System.nanoTime()
                                - startNs
                        ) / 1_000_000.0

                    inferenceTimes[
                        runIndex
                    ] = elapsedMs

                    @Suppress("UNCHECKED_CAST")
                    val output =
                        result[0].value
                            as Array<FloatArray>

                    require(
                        output.size == BATCH
                    ) {
                        "Expected 10 embeddings, got ${output.size}"
                    }

                    for (row in output) {

                        require(
                            row.size == EMBEDDING_SIZE
                        ) {
                            "Expected embedding length 512"
                        }
                    }

                    if (
                        runIndex ==
                        inferenceTimes.lastIndex
                    ) {

                        finalEmbeddings =
                            Array(BATCH) { row ->

                                output[row]
                                    .clone()
                            }
                    }
                }

                Log.i(
                    TAG,
                    "Measured run ${runIndex + 1}/3 | %.2f ms"
                        .format(
                            java.util.Locale.US,
                            inferenceTimes[runIndex]
                        )
                )
            }

            val embeddings =
                requireNotNull(
                    finalEmbeddings
                )

            val averageMs =
                inferenceTimes.average()

            val minMs =
                inferenceTimes.minOrNull()
                    ?: Double.NaN

            val maxMs =
                inferenceTimes.maxOrNull()
                    ?: Double.NaN

            Log.i(TAG, "----------------------------------------------")
            Log.i(TAG, "BATCH-7 PERFORMANCE")
            Log.i(TAG, "----------------------------------------------")

            Log.i(
                TAG,
                "Average inference : %.2f ms"
                    .format(
                        java.util.Locale.US,
                        averageMs
                    )
            )

            Log.i(
                TAG,
                "Fastest inference : %.2f ms"
                    .format(
                        java.util.Locale.US,
                        minMs
                    )
            )

            Log.i(
                TAG,
                "Slowest inference : %.2f ms"
                    .format(
                        java.util.Locale.US,
                        maxMs
                    )
            )

            // ========================================================
            // 6. NUMERICAL COMPARISON AGAINST COLAB ONNX
            // ========================================================

            var globalMaxAbsError = 0.0
            var globalAbsErrorSum = 0.0
            var globalValueCount = 0

            var minimumCosine =
                Double.POSITIVE_INFINITY

            var cosineSum = 0.0

            for (row in 0 until BATCH) {

                var dot = 0.0
                var androidNormSq = 0.0
                var referenceNormSq = 0.0

                for (
                    column in
                    0 until EMBEDDING_SIZE
                ) {

                    val androidValue =
                        embeddings[row][column]
                            .toDouble()

                    val referenceValue =
                        referenceEmbeddings[
                            row * EMBEDDING_SIZE
                                + column
                        ].toDouble()

                    require(
                        androidValue.isFinite()
                    ) {
                        "Android embedding contains non-finite value"
                    }

                    val difference =
                        abs(
                            androidValue
                                - referenceValue
                        )

                    globalMaxAbsError =
                        max(
                            globalMaxAbsError,
                            difference
                        )

                    globalAbsErrorSum +=
                        difference

                    globalValueCount++

                    dot +=
                        androidValue *
                            referenceValue

                    androidNormSq +=
                        androidValue *
                            androidValue

                    referenceNormSq +=
                        referenceValue *
                            referenceValue
                }

                val cosine =
                    dot /
                        (
                            sqrt(androidNormSq) *
                                sqrt(referenceNormSq)
                        )

                minimumCosine =
                    kotlin.math.min(
                        minimumCosine,
                        cosine
                    )

                cosineSum +=
                    cosine

                Log.i(
                    TAG,
                    "Row ${row + 1} cosine = %.12f"
                        .format(
                            java.util.Locale.US,
                            cosine
                        )
                )
            }

            val meanAbsError =
                globalAbsErrorSum /
                    globalValueCount

            val meanCosine =
                cosineSum /
                    BATCH

            Log.i(TAG, "----------------------------------------------")
            Log.i(TAG, "COLAB ↔ S21 NUMERICAL COMPARISON")
            Log.i(TAG, "----------------------------------------------")

            Log.i(
                TAG,
                "Max abs error : %.12g"
                    .format(
                        java.util.Locale.US,
                        globalMaxAbsError
                    )
            )

            Log.i(
                TAG,
                "Mean abs error: %.12g"
                    .format(
                        java.util.Locale.US,
                        meanAbsError
                    )
            )

            Log.i(
                TAG,
                "Min row cosine: %.12f"
                    .format(
                        java.util.Locale.US,
                        minimumCosine
                    )
            )

            Log.i(
                TAG,
                "Mean cosine   : %.12f"
                    .format(
                        java.util.Locale.US,
                        meanCosine
                    )
            )

            // ========================================================
            // 7. SEMANTIC RERANKING ON S9
            // ========================================================

            var winnerRank = -1

            var winnerMargin =
                Float.NEGATIVE_INFINITY

            for (row in 0 until BATCH) {

                val embedding =
                    embeddings[row]

                var normSq = 0.0

                for (value in embedding) {

                    normSq +=
                        value.toDouble() *
                            value.toDouble()
                }

                val norm =
                    sqrt(normSq)

                require(
                    norm.isFinite()
                        && norm > 0.0
                ) {
                    "Invalid embedding norm"
                }

                val similarities =
                    FloatArray(
                        PROMPT_COUNT
                    )

                for (
                    prompt in
                    0 until PROMPT_COUNT
                ) {

                    var dot = 0.0

                    for (
                        column in
                        0 until EMBEDDING_SIZE
                    ) {

                        val normalizedValue =
                            embedding[column]
                                .toDouble() /
                                norm

                        val textValue =
                            textFeatures[
                                prompt *
                                    EMBEDDING_SIZE
                                    + column
                            ].toDouble()

                        dot +=
                            normalizedValue *
                                textValue
                    }

                    similarities[prompt] =
                        dot.toFloat()
                }

                val phoneScore =
                    maxOf(
                        similarities[0],
                        similarities[1]
                    )

                val negativeScore =
                    maxOf(
                        similarities[2],
                        similarities[3],
                        similarities[4],
                        similarities[5]
                    )

                val margin =
                    phoneScore -
                        negativeScore

                Log.i(
                    TAG,
                    "Rank ${row + 1} | " +
                        "phone=%.9f | ".format(
                            java.util.Locale.US,
                            phoneScore
                        ) +
                        "negative=%.9f | ".format(
                            java.util.Locale.US,
                            negativeScore
                        ) +
                        "margin=%+.9f".format(
                            java.util.Locale.US,
                            margin
                        )
                )

                if (
                    margin >
                    winnerMargin
                ) {

                    winnerMargin =
                        margin

                    winnerRank =
                        row + 1
                }
            }

            // ========================================================
            // 8. FINAL RESULT
            // ========================================================

            Log.i(TAG, "----------------------------------------------")
            Log.i(TAG, "D1-L8I S21 RESULT")
            Log.i(TAG, "----------------------------------------------")

            Log.i(
                TAG,
                "Winner rank   : $winnerRank"
            )

            Log.i(
                TAG,
                "Winner margin : %+.9f"
                    .format(
                        java.util.Locale.US,
                        winnerMargin
                    )
            )

            Log.i(
                TAG,
                "Reference rank: $EXPECTED_WINNER_RANK"
            )

            Log.i(
                TAG,
                "Margin >= +0.005: ${
                    winnerMargin >= MARGIN_REFERENCE
                }"
            )

            val pass =
                winnerRank ==
                    EXPECTED_WINNER_RANK &&
                    winnerMargin >=
                    MARGIN_REFERENCE &&
                    minimumCosine >
                    0.99999 &&
                    embeddings.all { row ->
                        row.all {
                            it.isFinite()
                        }
                    }

            if (pass) {

                Log.i(
                    TAG,
                    "D1-L8I RESULT: PASS"
                )

            } else {

                Log.e(
                    TAG,
                    "D1-L8I RESULT: FAIL"
                )
            }

        } catch (t: Throwable) {

            Log.e(
                TAG,
                "D1-L8I RESULT: FAIL",
                t
            )

        } finally {

            try {
                inputTensor?.close()
            } catch (_: Throwable) {
            }

            try {
                session?.close()
            } catch (_: Throwable) {
            }

            Log.i(
                TAG,
                "============================================================"
            )

            Log.i(
                TAG,
                "D1-L8I BATCH-7 PROBE COMPLETE"
            )

            Log.i(
                TAG,
                "============================================================"
            )
        }
    }


    private fun loadFloatAsset(
        context: Context,
        assetName: String,
        expectedFloatCount: Int
    ): FloatArray {

        val bytes =
            context.assets
                .open(assetName)
                .use {
                    it.readBytes()
                }

        val expectedBytes =
            expectedFloatCount * 4

        require(
            bytes.size ==
                expectedBytes
        ) {
            "$assetName size mismatch: " +
                "${bytes.size} != $expectedBytes"
        }

        val floats =
            FloatArray(
                expectedFloatCount
            )

        ByteBuffer.wrap(bytes)
            .order(
                ByteOrder.LITTLE_ENDIAN
            )
            .asFloatBuffer()
            .get(floats)

        return floats
    }
}
