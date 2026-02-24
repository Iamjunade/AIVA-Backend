package com.aiva.core.camera

import android.content.Context
import android.graphics.ImageFormat
import android.graphics.Rect
import android.graphics.YuvImage
import android.util.Size
import androidx.camera.core.CameraSelector
import androidx.camera.core.ImageAnalysis
import androidx.camera.core.ImageProxy
import androidx.camera.core.Preview
import androidx.camera.lifecycle.ProcessCameraProvider
import androidx.core.content.ContextCompat
import kotlinx.coroutines.channels.BufferOverflow
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableSharedFlow
import timber.log.Timber
import java.io.ByteArrayOutputStream
import java.util.concurrent.Executors

class CameraManager(private val context: Context) {

    var surfaceProvider: Preview.SurfaceProvider? = null

    private val _frameFlow = MutableSharedFlow<ByteArray>(
        replay = 0,
        extraBufferCapacity = 1, // Ensure buffer is positive
        onBufferOverflow = BufferOverflow.DROP_OLDEST
    )
    val frameFlow: Flow<ByteArray> = _frameFlow

    private val executor = Executors.newSingleThreadExecutor()
    private val outputStream = ByteArrayOutputStream(40000) // Pre-allocate ~40KB
    private var cameraProvider: ProcessCameraProvider? = null

    fun startCamera(lifecycleOwner: androidx.lifecycle.LifecycleOwner) {
        val cameraProviderFuture = ProcessCameraProvider.getInstance(context)

        cameraProviderFuture.addListener({
            cameraProvider = cameraProviderFuture.get()

            // 640x480 resolution (Level C Constraint)
            // KEEP_ONLY_LATEST (Drop Queue)
            val imageAnalysis = ImageAnalysis.Builder()
                .setTargetResolution(Size(640, 480))
                .setBackpressureStrategy(ImageAnalysis.STRATEGY_KEEP_ONLY_LATEST)
                .setOutputImageFormat(ImageAnalysis.OUTPUT_IMAGE_FORMAT_YUV_420_888)
                .build()

            imageAnalysis.setAnalyzer(executor) { image ->
                processImage(image)
            }

            val useCases = mutableListOf<androidx.camera.core.UseCase>(imageAnalysis)
            
            // If the UI has passed us a View connection, bind the Preview use-case too
            if (surfaceProvider != null) {
                val preview = Preview.Builder().build()
                preview.setSurfaceProvider(surfaceProvider)
                useCases.add(preview)
            }

            try {
                cameraProvider?.unbindAll()
                cameraProvider?.bindToLifecycle(
                    lifecycleOwner,
                    CameraSelector.DEFAULT_BACK_CAMERA,
                    *useCases.toTypedArray()
                )
                Timber.i("Camera bound (640x480)")
            } catch (exc: Exception) {
                Timber.e(exc, "Camera binding failed")
            }

        }, ContextCompat.getMainExecutor(context))
    }

    fun stopCamera() {
        cameraProvider?.unbindAll()
        Timber.i("Camera unbound")
    }

    private fun processImage(image: ImageProxy) {
        try {
            // YUV_420_888 to JPEG conversion (stride-aware)
            if (image.format != ImageFormat.YUV_420_888) {
                Timber.e("Invalid format: ${image.format}")
                return
            }

            val width = image.width
            val height = image.height

            val yPlane = image.planes[0]
            val uPlane = image.planes[1]
            val vPlane = image.planes[2]

            // Build NV21 array with proper stride handling.
            // Some devices (Pixel, Samsung) have pixelStride=2 and rowStride != width,
            // which the naive buffer.get() approach mishandles, producing corrupt images.
            val nv21 = ByteArray(width * height + width * height / 2)

            // Copy Y plane row-by-row (respects rowStride)
            val yBuffer = yPlane.buffer
            val yRowStride = yPlane.rowStride
            for (row in 0 until height) {
                yBuffer.position(row * yRowStride)
                yBuffer.get(nv21, row * width, width)
            }

            // Interleave V and U into NV21 format (respects pixelStride)
            val vBuffer = vPlane.buffer
            val uBuffer = uPlane.buffer
            val uvPixelStride = vPlane.pixelStride
            val uvRowStride = vPlane.rowStride
            val uvHeight = height / 2
            var uvOffset = width * height

            for (row in 0 until uvHeight) {
                for (col in 0 until width / 2) {
                    val bufferIndex = row * uvRowStride + col * uvPixelStride
                    nv21[uvOffset++] = vBuffer.get(bufferIndex)
                    nv21[uvOffset++] = uBuffer.get(bufferIndex)
                }
            }

            val yuvImage = YuvImage(nv21, ImageFormat.NV21, width, height, null)

            // Adaptive JPEG quality: start at 75, reduce to 50 if payload > 45KB
            outputStream.reset()
            yuvImage.compressToJpeg(Rect(0, 0, width, height), 75, outputStream)
            var jpegBytes = outputStream.toByteArray()

            if (jpegBytes.size > 45_000) {
                outputStream.reset()
                yuvImage.compressToJpeg(Rect(0, 0, width, height), 50, outputStream)
                jpegBytes = outputStream.toByteArray()
            }

            // Emit to flow (non-blocking)
            _frameFlow.tryEmit(jpegBytes)

        } catch (e: Exception) {
            Timber.e(e, "Compression failed")
        } finally {
            image.close()
        }
    }
}
