package com.aiva.core.ml

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.Data
import androidx.work.ForegroundInfo
import androidx.work.WorkerParameters
import androidx.work.workDataOf
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import androidx.core.app.NotificationCompat
import timber.log.Timber
import java.io.File
import java.io.FileOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.security.MessageDigest

/**
 * AIVA — Background Model Download Worker
 *
 * Uses WorkManager to download edge AI models post-installation.
 * Runs with network + battery constraints, supports resume on interruption,
 * and validates SHA-256 hash after download.
 *
 * Enqueue from Application or ViewModel:
 * ```kotlin
 * val request = OneTimeWorkRequestBuilder<ModelDownloadWorker>()
 *     .setConstraints(Constraints.Builder()
 *         .setRequiredNetworkType(NetworkType.CONNECTED)
 *         .setRequiresBatteryNotLow(true)
 *         .build())
 *     .build()
 * WorkManager.getInstance(context).enqueueUniqueWork(
 *     ModelDownloadWorker.WORK_NAME,
 *     ExistingWorkPolicy.KEEP,
 *     request
 * )
 * ```
 */
class ModelDownloadWorker(
    appContext: Context,
    params: WorkerParameters
) : CoroutineWorker(appContext, params) {

    companion object {
        const val WORK_NAME = "aiva_model_download"
        const val CHANNEL_ID = "aiva_model_download_channel"
        const val NOTIFICATION_ID = 42

        // Progress keys (observed via WorkManager.getWorkInfoByIdLiveData)
        const val KEY_MODEL_NAME = "model_name"
        const val KEY_PROGRESS = "progress"
        const val KEY_BYTES_DOWNLOADED = "bytes_downloaded"
        const val KEY_TOTAL_BYTES = "total_bytes"

        /**
         * Models to download. Each entry: (filename, URL, expected SHA-256).
         * Add edge TFLite models here as they become available.
         */
        private val MODELS = listOf(
            ModelSpec(
                name = "YOLOv8n TFLite",
                filename = "yolov8n_float16.tflite",
                url = "https://github.com/ultralytics/assets/releases/download/v8.1.0/yolov8n_float16.tflite",
                sha256 = null, // Set once known
                sizeBytes = 6_400_000L,
            ),
            // Add more edge models as needed:
            // ModelSpec(
            //     name = "MiDaS Small TFLite",
            //     filename = "midas_small.tflite",
            //     url = "...",
            //     sha256 = "...",
            //     sizeBytes = 50_000_000L,
            // ),
        )
    }

    override suspend fun doWork(): Result {
        Timber.i("ModelDownloadWorker started (attempt ${runAttemptCount + 1})")

        createNotificationChannel()
        setForeground(createForegroundInfo("Preparing model download..."))

        val modelsDir = File(applicationContext.filesDir, "models")
        modelsDir.mkdirs()

        var completed = 0

        for ((index, spec) in MODELS.withIndex()) {
            val targetFile = File(modelsDir, spec.filename)

            // Skip if already downloaded and verified
            if (targetFile.exists() && targetFile.length() > 0) {
                if (spec.sha256 == null || verifyHash(targetFile, spec.sha256)) {
                    Timber.i("  ✓ ${spec.name} already cached")
                    completed++
                    continue
                } else {
                    Timber.w("  ⚠ ${spec.name} hash mismatch — re-downloading")
                    targetFile.delete()
                }
            }

            // Report progress
            setProgress(workDataOf(
                KEY_MODEL_NAME to spec.name,
                KEY_PROGRESS to (index * 100 / MODELS.size),
                KEY_BYTES_DOWNLOADED to 0L,
                KEY_TOTAL_BYTES to spec.sizeBytes,
            ))
            setForeground(createForegroundInfo("Downloading ${spec.name}..."))

            try {
                downloadFile(spec.url, targetFile, spec.sizeBytes) { downloaded, total ->
                    setProgress(workDataOf(
                        KEY_MODEL_NAME to spec.name,
                        KEY_PROGRESS to ((downloaded * 100) / total).toInt(),
                        KEY_BYTES_DOWNLOADED to downloaded,
                        KEY_TOTAL_BYTES to total,
                    ))
                }

                // Verify hash if specified
                if (spec.sha256 != null && !verifyHash(targetFile, spec.sha256)) {
                    Timber.e("  ✗ ${spec.name} hash verification failed")
                    targetFile.delete()
                    return Result.retry()
                }

                completed++
                Timber.i("  ✓ ${spec.name} downloaded (${targetFile.length() / 1024}KB)")

            } catch (e: Exception) {
                Timber.e(e, "  ✗ Failed to download ${spec.name}")
                return if (runAttemptCount < 3) Result.retry() else Result.failure(
                    workDataOf("error" to e.message)
                )
            }
        }

        Timber.i("ModelDownloadWorker completed: $completed/${MODELS.size} models")
        return Result.success(workDataOf(
            KEY_PROGRESS to 100,
            "model_count" to completed,
        ))
    }

    /**
     * Download a file with progress callback. Supports resume via Range header.
     */
    private fun downloadFile(
        urlStr: String,
        target: File,
        expectedSize: Long,
        onProgress: (downloaded: Long, total: Long) -> Unit
    ) {
        val tempFile = File(target.parent, "${target.name}.tmp")
        val startByte = if (tempFile.exists()) tempFile.length() else 0L

        val connection = URL(urlStr).openConnection() as HttpURLConnection
        connection.connectTimeout = 15_000
        connection.readTimeout = 30_000
        if (startByte > 0) {
            connection.setRequestProperty("Range", "bytes=$startByte-")
        }

        connection.connect()
        val responseCode = connection.responseCode

        if (responseCode !in listOf(200, 206)) {
            throw RuntimeException("HTTP $responseCode for $urlStr")
        }

        val totalBytes = if (responseCode == 206) {
            startByte + connection.contentLength
        } else {
            connection.contentLength.toLong().takeIf { it > 0 } ?: expectedSize
        }

        connection.inputStream.use { input ->
            FileOutputStream(tempFile, startByte > 0).use { output ->
                val buffer = ByteArray(8192)
                var downloaded = startByte

                while (true) {
                    val bytesRead = input.read(buffer)
                    if (bytesRead == -1) break
                    output.write(buffer, 0, bytesRead)
                    downloaded += bytesRead
                    onProgress(downloaded, totalBytes)
                }
            }
        }

        // Atomic rename
        tempFile.renameTo(target)
    }

    /**
     * Verify SHA-256 hash of a downloaded file.
     */
    private fun verifyHash(file: File, expectedHash: String): Boolean {
        val digest = MessageDigest.getInstance("SHA-256")
        file.inputStream().use { input ->
            val buffer = ByteArray(8192)
            while (true) {
                val bytesRead = input.read(buffer)
                if (bytesRead == -1) break
                digest.update(buffer, 0, bytesRead)
            }
        }
        val actualHash = digest.digest().joinToString("") { "%02x".format(it) }
        return actualHash.equals(expectedHash, ignoreCase = true)
    }

    /**
     * Create foreground notification for long-running download.
     */
    private fun createForegroundInfo(title: String): ForegroundInfo {
        val notification = NotificationCompat.Builder(applicationContext, CHANNEL_ID)
            .setContentTitle("AIVA Model Download")
            .setContentText(title)
            .setSmallIcon(android.R.drawable.stat_sys_download)
            .setOngoing(true)
            .setPriority(NotificationCompat.PRIORITY_LOW)
            .build()
        return ForegroundInfo(NOTIFICATION_ID, notification)
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "Model Downloads",
                NotificationManager.IMPORTANCE_LOW
            ).apply {
                description = "Background AI model downloads"
            }
            val manager = applicationContext.getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }
    }

    /**
     * Specification for a downloadable model.
     */
    private data class ModelSpec(
        val name: String,
        val filename: String,
        val url: String,
        val sha256: String?,
        val sizeBytes: Long,
    )
}
