package com.guardianlab.app

import android.content.Context
import android.util.Log
import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.FloatBuffer
import java.util.Locale
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.sqrt

object MobileClipSequential7Probe {

    private const val TAG =
        "GL_MOBILECLIP_SEQ7"

    private const val MODEL_ASSET =
        "D1_K7W_MOBILECLIP2_S0_VISUAL_FP32_EMBEDDED.onnx"

    private const val INPUT_ASSET =
        "d1_l8i_frame060_top7_input_fp32.bin"

    private const val TEXT_ASSET =
        "d1_l8i_text_features_fp32.bin"

    private const val REFERENCE_ASSET =
        "d1_l8i_onnx_reference_embeddings_fp32.bin"

    private const val MAX_RANK = 7

    private const val CHANNELS = 3
    private const val HEIGHT = 256
    private const val WIDTH = 256

    private const val EMBEDDING_SIZE = 512
    private const val PROMPT_COUNT = 6

    private const val FLOATS_PER_CROP =
        CHANNELS * HEIGHT * WIDTH

    private const val MARGIN_THRESHOLD =
        0.005f

    private const val EXPECTED_TRIGGER_RANK =
        7

    fun run(context: Context) {

        Log.i(TAG, "============================================================")
        Log.i(TAG, "GUARDIANLAB — D1-L8L")
        Log.i(TAG, "GALAXY S21 SEQUENTIAL TOP-7 EARLY-EXIT VALIDATION")
        Log.i(TAG, "F060 | EXPECTED FIRST TRIGGER = RANK 7")
        Log.i(TAG, "CPU ONLY | THREADS=2 | ORT ALL_OPT")
        Log.i(TAG, "============================================================")

        var session: OrtSession? = null

        val tensors =
            mutableListOf<OnnxTensor>()

        try {

            val inputData =
                loadFloatAsset(
                    context,
                    INPUT_ASSET,
                    MAX_RANK * FLOATS_PER_CROP
                )

            val textFeatures =
                loadFloatAsset(
                    context,
                    TEXT_ASSET,
                    PROMPT_COUNT * EMBEDDING_SIZE
                )

            val referenceEmbeddings =
                loadFloatAsset(
                    context,
                    REFERENCE_ASSET,
                    MAX_RANK * EMBEDDING_SIZE
                )

            Log.i(
                TAG,
                "Assets PASS | input=${inputData.size} | " +
                    "text=${textFeatures.size} | " +
                    "reference=${referenceEmbeddings.size}"
            )

            val modelBytes =
                context.assets
                    .open(MODEL_ASSET)
                    .use { it.readBytes() }

            Log.i(
                TAG,
                "Model bytes: ${modelBytes.size}"
            )

            val environment =
                OrtEnvironment.getEnvironment()

            val options =
                OrtSession.SessionOptions().apply {

                    // IMPORTANT:
                    // Controlled CPU-only execution.
                    // Do NOT enable NNAPI.

                    setIntraOpNumThreads(2)

                    setOptimizationLevel(
                        OrtSession.SessionOptions
                            .OptLevel.ALL_OPT
                    )
                }

            val loadStart =
                System.nanoTime()

            session =
                environment.createSession(
                    modelBytes,
                    options
                )

            val loadMs =
                (
                    System.nanoTime() -
                        loadStart
                ) / 1_000_000.0

            Log.i(
                TAG,
                "ORT session load PASS | %.2f ms"
                    .format(
                        Locale.US,
                        loadMs
                    )
            )

            // ========================================================
            // CREATE SEVEN SEPARATE [1,3,256,256] TENSORS
            // ========================================================

            for (rank in 0 until MAX_RANK) {

                val start =
                    rank * FLOATS_PER_CROP

                val end =
                    start + FLOATS_PER_CROP

                val cropData =
                    inputData.copyOfRange(
                        start,
                        end
                    )

                val tensor =
                    OnnxTensor.createTensor(
                        environment,
                        FloatBuffer.wrap(cropData),
                        longArrayOf(
                            1L,
                            CHANNELS.toLong(),
                            HEIGHT.toLong(),
                            WIDTH.toLong()
                        )
                    )

                tensors.add(tensor)
            }

            Log.i(
                TAG,
                "Tensor creation PASS | 7 × [1,3,256,256]"
            )

            // ========================================================
            // WARM-UP USING RANK 1 ONLY
            // ========================================================

            val warmupStart =
                System.nanoTime()

            session.run(
                mapOf(
                    "image" to tensors[0]
                )
            ).use { result ->

                @Suppress("UNCHECKED_CAST")
                val output =
                    result[0].value
                        as Array<FloatArray>

                require(
                    output.size == 1 &&
                        output[0].size ==
                        EMBEDDING_SIZE
                )
            }

            val warmupMs =
                (
                    System.nanoTime() -
                        warmupStart
                ) / 1_000_000.0

            Log.i(
                TAG,
                "Warm-up PASS | %.2f ms"
                    .format(
                        Locale.US,
                        warmupMs
                    )
            )

            // ========================================================
            // THREE MEASURED SEQUENTIAL PASSES
            // ========================================================

            val totalTimes =
                DoubleArray(3)

            var globalMinimumCosine =
                Double.POSITIVE_INFINITY

            var globalMaxAbsError =
                0.0

            var finalTriggerRank =
                -1

            for (passIndex in 0 until 3) {

                Log.i(
                    TAG,
                    "----------------------------------------------"
                )

                Log.i(
                    TAG,
                    "SEQUENTIAL PASS ${passIndex + 1}/3"
                )

                Log.i(
                    TAG,
                    "----------------------------------------------"
                )

                val passStart =
                    System.nanoTime()

                var triggerRank =
                    -1

                for (rankIndex in 0 until MAX_RANK) {

                    val rankStart =
                        System.nanoTime()

                    val embedding =
                        session.run(
                            mapOf(
                                "image" to
                                    tensors[rankIndex]
                            )
                        ).use { result ->

                            @Suppress("UNCHECKED_CAST")
                            val output =
                                result[0].value
                                    as Array<FloatArray>

                            require(
                                output.size == 1
                            ) {
                                "Expected one embedding"
                            }

                            require(
                                output[0].size ==
                                    EMBEDDING_SIZE
                            ) {
                                "Expected embedding length 512"
                            }

                            output[0].clone()
                        }

                    val rankMs =
                        (
                            System.nanoTime() -
                                rankStart
                        ) / 1_000_000.0

                    // ================================================
                    // NUMERICAL COMPARISON TO FROZEN COLAB REFERENCE
                    // ================================================

                    var dotReference = 0.0
                    var androidNormSq = 0.0
                    var referenceNormSq = 0.0

                    for (
                        column in
                        0 until EMBEDDING_SIZE
                    ) {

                        val androidValue =
                            embedding[column]
                                .toDouble()

                        require(
                            androidValue.isFinite()
                        ) {
                            "Non-finite Android embedding"
                        }

                        val referenceValue =
                            referenceEmbeddings[
                                rankIndex *
                                    EMBEDDING_SIZE +
                                    column
                            ].toDouble()

                        val error =
                            abs(
                                androidValue -
                                    referenceValue
                            )

                        globalMaxAbsError =
                            max(
                                globalMaxAbsError,
                                error
                            )

                        dotReference +=
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
                        dotReference /
                            (
                                sqrt(androidNormSq) *
                                    sqrt(referenceNormSq)
                            )

                    globalMinimumCosine =
                        kotlin.math.min(
                            globalMinimumCosine,
                            cosine
                        )

                    // ================================================
                    // EXACT PROVEN MOBILECLIP SEMANTIC SCORING
                    // ================================================

                    var embeddingNormSq =
                        0.0

                    for (value in embedding) {

                        embeddingNormSq +=
                            value.toDouble() *
                                value.toDouble()
                    }

                    val embeddingNorm =
                        sqrt(
                            embeddingNormSq
                        )

                    require(
                        embeddingNorm.isFinite()
                            && embeddingNorm > 0.0
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

                        var dot =
                            0.0

                        for (
                            column in
                            0 until EMBEDDING_SIZE
                        ) {

                            val normalizedValue =
                                embedding[column]
                                    .toDouble() /
                                    embeddingNorm

                            val textValue =
                                textFeatures[
                                    prompt *
                                        EMBEDDING_SIZE +
                                        column
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
                        "Pass ${passIndex + 1} | " +
                            "Rank ${rankIndex + 1} | " +
                            "time=%.2f ms | "
                                .format(
                                    Locale.US,
                                    rankMs
                                ) +
                            "cos=%.12f | "
                                .format(
                                    Locale.US,
                                    cosine
                                ) +
                            "margin=%+.9f"
                                .format(
                                    Locale.US,
                                    margin
                                )
                    )

                    // ================================================
                    // EARLY EXIT
                    // ================================================

                    if (
                        margin >=
                            MARGIN_THRESHOLD
                    ) {

                        triggerRank =
                            rankIndex + 1

                        Log.i(
                            TAG,
                            "EARLY EXIT TRIGGER | " +
                                "rank=$triggerRank | " +
                                "margin=%+.9f"
                                    .format(
                                        Locale.US,
                                        margin
                                    )
                        )

                        break
                    }
                }

                val totalMs =
                    (
                        System.nanoTime() -
                            passStart
                    ) / 1_000_000.0

                totalTimes[
                    passIndex
                ] = totalMs

                finalTriggerRank =
                    triggerRank

                Log.i(
                    TAG,
                    "Pass ${passIndex + 1} total | " +
                        "%.2f ms | triggerRank=$triggerRank"
                            .format(
                                Locale.US,
                                totalMs
                            )
                )
            }

            val averageMs =
                totalTimes.average()

            val fastestMs =
                totalTimes.minOrNull()
                    ?: Double.NaN

            val slowestMs =
                totalTimes.maxOrNull()
                    ?: Double.NaN

            Log.i(
                TAG,
                "----------------------------------------------"
            )

            Log.i(
                TAG,
                "D1-L8L SEQUENTIAL PERFORMANCE"
            )

            Log.i(
                TAG,
                "----------------------------------------------"
            )

            Log.i(
                TAG,
                "Average total : %.2f ms"
                    .format(
                        Locale.US,
                        averageMs
                    )
            )

            Log.i(
                TAG,
                "Fastest total : %.2f ms"
                    .format(
                        Locale.US,
                        fastestMs
                    )
            )

            Log.i(
                TAG,
                "Slowest total : %.2f ms"
                    .format(
                        Locale.US,
                        slowestMs
                    )
            )

            Log.i(
                TAG,
                "Minimum cosine: %.12f"
                    .format(
                        Locale.US,
                        globalMinimumCosine
                    )
            )

            Log.i(
                TAG,
                "Max abs error : %.12g"
                    .format(
                        Locale.US,
                        globalMaxAbsError
                    )
            )

            Log.i(
                TAG,
                "Trigger rank  : $finalTriggerRank"
            )

            val pass =
                finalTriggerRank ==
                    EXPECTED_TRIGGER_RANK &&
                    globalMinimumCosine >
                    0.99999

            if (pass) {

                Log.i(
                    TAG,
                    "D1-L8L RESULT: PASS"
                )

            } else {

                Log.e(
                    TAG,
                    "D1-L8L RESULT: FAIL"
                )
            }

        } catch (t: Throwable) {

            Log.e(
                TAG,
                "D1-L8L RESULT: FAIL",
                t
            )

        } finally {

            for (tensor in tensors) {

                try {
                    tensor.close()
                } catch (_: Throwable) {
                }
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
                "D1-L8L SEQUENTIAL PROBE COMPLETE"
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
                .use { it.readBytes() }

        require(
            bytes.size ==
                expectedFloatCount * 4
        ) {
            "$assetName expected " +
                "${expectedFloatCount * 4} bytes, " +
                "got ${bytes.size}"
        }

        val buffer =
            ByteBuffer
                .wrap(bytes)
                .order(
                    ByteOrder.LITTLE_ENDIAN
                )
                .asFloatBuffer()

        val output =
            FloatArray(
                expectedFloatCount
            )

        buffer.get(output)

        return output
    }
}
