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

object MobileClipBatchScalingProbe {

    private const val TAG =
        "GL_MOBILECLIP_SCALING"

    private const val MODEL_ASSET =
        "D1_K7W_MOBILECLIP2_S0_VISUAL_FP32_EMBEDDED.onnx"

    private const val INPUT_ASSET =
        "d1_l8i_frame060_top7_input_fp32.bin"

    private const val CHANNELS = 3
    private const val HEIGHT = 256
    private const val WIDTH = 256
    private const val EMBEDDING_SIZE = 512

    private const val MAX_BATCH = 7

    private const val FLOATS_PER_ITEM =
        CHANNELS * HEIGHT * WIDTH

    private const val EXPECTED_INPUT_FLOATS =
        MAX_BATCH * FLOATS_PER_ITEM

    private val BATCHES =
        intArrayOf(
            1,
            2,
            4,
            7
        )

    /*
     * Balanced four-round order.
     *
     * Each batch appears once in each approximate
     * early/middle/late position across the benchmark.
     *
     * This reduces the chance that simple test order
     * is mistaken for a batch-size effect.
     */
    private val MEASUREMENT_SCHEDULE =
        arrayOf(
            intArrayOf(1, 2, 4, 7),
            intArrayOf(2, 7, 1, 4),
            intArrayOf(4, 1, 7, 2),
            intArrayOf(7, 4, 2, 1)
        )

    fun run(
        context: Context
    ) {

        Log.i(
            TAG,
            "============================================================"
        )

        Log.i(
            TAG,
            "GUARDIANLAB — D1-L8J"
        )

        Log.i(
            TAG,
            "GALAXY S21 MOBILECLIP FP32 BATCH-SCALING BENCHMARK"
        )

        Log.i(
            TAG,
            "BATCHES = 1, 2, 4, 7"
        )

        Log.i(
            TAG,
            "CPU ONLY | THREADS=2 | ORT ALL_OPT"
        )

        Log.i(
            TAG,
            "============================================================"
        )

        try {

            // ========================================================
            // 1. LOAD EXACT FROZEN TOP-7 INPUT
            // ========================================================

            val inputData =
                readFloatAsset(
                    context,
                    INPUT_ASSET
                )

            require(
                inputData.size ==
                    EXPECTED_INPUT_FLOATS
            ) {
                "Expected $EXPECTED_INPUT_FLOATS input floats, " +
                    "got ${inputData.size}"
            }

            Log.i(
                TAG,
                "Input floats: ${inputData.size}"
            )

            Log.i(
                TAG,
                "Input asset validation: PASS"
            )

            // ========================================================
            // 2. LOAD EXACT FP32 VISUAL MODEL
            // ========================================================

            val modelBytes =
                context.assets
                    .open(
                        MODEL_ASSET
                    )
                    .use {
                        it.readBytes()
                    }

            Log.i(
                TAG,
                "Model bytes: ${modelBytes.size}"
            )

            val environment =
                OrtEnvironment
                    .getEnvironment()

            val options =
                OrtSession
                    .SessionOptions()
                    .apply {

                        // IMPORTANT:
                        // CPU-only control.
                        // DO NOT enable NNAPI.

                        setIntraOpNumThreads(
                            2
                        )

                        setOptimizationLevel(
                            OrtSession.SessionOptions
                                .OptLevel.ALL_OPT
                        )
                    }

            try {

                val sessionLoadStart =
                    System.nanoTime()

                val session =
                    environment
                        .createSession(
                            modelBytes,
                            options
                        )

                try {

                    val sessionLoadMs =
                        (
                            System.nanoTime()
                                - sessionLoadStart
                        ) / 1_000_000.0

                    Log.i(
                        TAG,
                        "ORT session load PASS | %.2f ms"
                            .format(
                                Locale.US,
                                sessionLoadMs
                            )
                    )

                    // =================================================
                    // 3. PRE-CREATE ALL FOUR INPUT TENSORS
                    //
                    // Tensor construction is intentionally OUTSIDE
                    // measured inference time.
                    // =================================================

                    val tensors =
                        linkedMapOf<
                            Int,
                            OnnxTensor
                        >()

                    try {

                        for (
                            batch in BATCHES
                        ) {

                            val floatCount =
                                batch *
                                    FLOATS_PER_ITEM

                            val batchData =
                                inputData.copyOfRange(
                                    0,
                                    floatCount
                                )

                            val shape =
                                longArrayOf(
                                    batch.toLong(),
                                    CHANNELS.toLong(),
                                    HEIGHT.toLong(),
                                    WIDTH.toLong()
                                )

                            val tensor =
                                OnnxTensor
                                    .createTensor(
                                        environment,
                                        FloatBuffer.wrap(
                                            batchData
                                        ),
                                        shape
                                    )

                            tensors[
                                batch
                            ] = tensor

                            Log.i(
                                TAG,
                                "Tensor PASS | " +
                                    "batch=$batch | " +
                                    "shape=[$batch,3,256,256]"
                            )
                        }

                        // =============================================
                        // 4. ONE WARM-UP FOR EACH BATCH SIZE
                        // =============================================

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        Log.i(
                            TAG,
                            "WARM-UP PHASE"
                        )

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        for (
                            batch in BATCHES
                        ) {

                            val tensor =
                                requireNotNull(
                                    tensors[
                                        batch
                                    ]
                                )

                            val startNs =
                                System.nanoTime()

                            session.run(
                                mapOf(
                                    "image" to tensor
                                )
                            ).use {
                                result ->

                                val elapsedMs =
                                    (
                                        System.nanoTime()
                                            - startNs
                                    ) / 1_000_000.0

                                validateResult(
                                    result,
                                    batch
                                )

                                Log.i(
                                    TAG,
                                    "Warm-up | " +
                                        "batch=$batch | " +
                                        "%.2f ms"
                                            .format(
                                                Locale.US,
                                                elapsedMs
                                            )
                                )
                            }
                        }

                        // =============================================
                        // 5. BALANCED MEASURED RUNS
                        // =============================================

                        val timings =
                            linkedMapOf<
                                Int,
                                MutableList<Double>
                            >()

                        for (
                            batch in BATCHES
                        ) {
                            timings[
                                batch
                            ] = mutableListOf()
                        }

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        Log.i(
                            TAG,
                            "MEASURED PHASE"
                        )

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        for (
                            roundIndex
                            in MEASUREMENT_SCHEDULE.indices
                        ) {

                            val order =
                                MEASUREMENT_SCHEDULE[
                                    roundIndex
                                ]

                            Log.i(
                                TAG,
                                "Round ${roundIndex + 1}/" +
                                    "${MEASUREMENT_SCHEDULE.size} | " +
                                    "order=${order.joinToString(",")}"
                            )

                            for (
                                batch in order
                            ) {

                                val tensor =
                                    requireNotNull(
                                        tensors[
                                            batch
                                        ]
                                    )

                                val startNs =
                                    System.nanoTime()

                                session.run(
                                    mapOf(
                                        "image" to tensor
                                    )
                                ).use {
                                    result ->

                                    val elapsedMs =
                                        (
                                            System.nanoTime()
                                                - startNs
                                        ) / 1_000_000.0

                                    validateResult(
                                        result,
                                        batch
                                    )

                                    timings
                                        .getValue(
                                            batch
                                        )
                                        .add(
                                            elapsedMs
                                        )

                                    Log.i(
                                        TAG,
                                        "MEASURED | " +
                                            "round=${roundIndex + 1} | " +
                                            "batch=$batch | " +
                                            "%.2f ms"
                                                .format(
                                                    Locale.US,
                                                    elapsedMs
                                                )
                                    )
                                }
                            }
                        }

                        // =============================================
                        // 6. SUMMARY
                        // =============================================

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        Log.i(
                            TAG,
                            "D1-L8J BATCH-SCALING SUMMARY"
                        )

                        Log.i(
                            TAG,
                            "----------------------------------------------"
                        )

                        for (
                            batch in BATCHES
                        ) {

                            val values =
                                timings
                                    .getValue(
                                        batch
                                    )

                            require(
                                values.size ==
                                    MEASUREMENT_SCHEDULE.size
                            )

                            val average =
                                values.average()

                            val sorted =
                                values.sorted()

                            val median =
                                (
                                    sorted[1]
                                        + sorted[2]
                                ) / 2.0

                            val fastest =
                                sorted.first()

                            val slowest =
                                sorted.last()

                            val msPerCandidate =
                                average /
                                    batch.toDouble()

                            val candidatesPerSecond =
                                batch.toDouble() /
                                    (
                                        average /
                                            1000.0
                                    )

                            Log.i(
                                TAG,
                                "BATCH=$batch | " +
                                    "avg=%.2f ms | "
                                        .format(
                                            Locale.US,
                                            average
                                        ) +
                                    "median=%.2f ms | "
                                        .format(
                                            Locale.US,
                                            median
                                        ) +
                                    "min=%.2f ms | "
                                        .format(
                                            Locale.US,
                                            fastest
                                        ) +
                                    "max=%.2f ms | "
                                        .format(
                                            Locale.US,
                                            slowest
                                        ) +
                                    "ms/item=%.2f | "
                                        .format(
                                            Locale.US,
                                            msPerCandidate
                                        ) +
                                    "items/s=%.2f"
                                        .format(
                                            Locale.US,
                                            candidatesPerSecond
                                        )
                            )
                        }

                        Log.i(
                            TAG,
                            "D1-L8J RESULT: PASS"
                        )

                    } finally {

                        for (
                            tensor
                            in tensors.values
                        ) {
                            tensor.close()
                        }
                    }

                } finally {

                    session.close()
                }

            } finally {

                options.close()
            }

        } catch (
            t: Throwable
        ) {

            Log.e(
                TAG,
                "D1-L8J RESULT: FAIL",
                t
            )
        }

        Log.i(
            TAG,
            "============================================================"
        )

        Log.i(
            TAG,
            "D1-L8J SCALING PROBE COMPLETE"
        )

        Log.i(
            TAG,
            "============================================================"
        )
    }

    private fun validateResult(
        result: OrtSession.Result,
        expectedBatch: Int
    ) {

        @Suppress("UNCHECKED_CAST")
        val output =
            result[0].value
                as Array<FloatArray>

        require(
            output.size ==
                expectedBatch
        ) {
            "Expected $expectedBatch embeddings, " +
                "got ${output.size}"
        }

        for (
            rowIndex
            in output.indices
        ) {

            val row =
                output[
                    rowIndex
                ]

            require(
                row.size ==
                    EMBEDDING_SIZE
            ) {
                "Batch $expectedBatch row $rowIndex " +
                    "expected 512 values, got ${row.size}"
            }

            for (
                value in row
            ) {

                require(
                    value.isFinite()
                ) {
                    "Non-finite embedding value | " +
                        "batch=$expectedBatch | " +
                        "row=$rowIndex"
                }
            }
        }
    }

    private fun readFloatAsset(
        context: Context,
        assetName: String
    ): FloatArray {

        val bytes =
            context.assets
                .open(
                    assetName
                )
                .use {
                    it.readBytes()
                }

        require(
            bytes.size % 4 == 0
        ) {
            "Float asset byte count is not divisible by 4: " +
                bytes.size
        }

        val buffer =
            ByteBuffer
                .wrap(
                    bytes
                )
                .order(
                    ByteOrder.LITTLE_ENDIAN
                )
                .asFloatBuffer()

        val output =
            FloatArray(
                buffer.remaining()
            )

        buffer.get(
            output
        )

        return output
    }
}
