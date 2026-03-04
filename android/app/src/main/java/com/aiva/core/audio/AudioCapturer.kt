package com.aiva.core.audio

import android.annotation.SuppressLint
import android.media.AudioFormat
import android.media.AudioRecord
import android.media.MediaRecorder
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import timber.log.Timber
import java.io.ByteArrayOutputStream
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class AudioCapturer @Inject constructor() {

    private var audioRecord: AudioRecord? = null
    private var isRecording = false

    companion object {
        private const val SAMPLE_RATE = 16000 // Whisper expects 16kHz
        private const val CHANNEL_CONFIG = AudioFormat.CHANNEL_IN_MONO
        private const val AUDIO_FORMAT = AudioFormat.ENCODING_PCM_16BIT
    }

    private val minBufferSize = AudioRecord.getMinBufferSize(SAMPLE_RATE, CHANNEL_CONFIG, AUDIO_FORMAT)

    @SuppressLint("MissingPermission") // Caller MUST ensure RECORD_AUDIO is granted
    fun startRecording() {
        if (isRecording) {
            Timber.w("Audio capture is already running.")
            return
        }

        if (minBufferSize == AudioRecord.ERROR || minBufferSize == AudioRecord.ERROR_BAD_VALUE) {
            Timber.e("AudioRecord Error: Invalid Buffer Size")
            return
        }

        try {
            audioRecord = AudioRecord(
                MediaRecorder.AudioSource.MIC,
                SAMPLE_RATE,
                CHANNEL_CONFIG,
                AUDIO_FORMAT,
                minBufferSize * 2 // Double buffer to avoid overflows
            )

            if (audioRecord?.state != AudioRecord.STATE_INITIALIZED) {
                Timber.e("AudioRecord initialization failed!")
                audioRecord?.release()
                audioRecord = null
                return
            }

            audioRecord?.startRecording()
            isRecording = true
            Timber.i("Started capturing audio at 16kHz PCM 16-bit Mono")

        } catch (e: Exception) {
            Timber.e(e, "Exception starting audio recording")
            isRecording = false
            audioRecord?.release()
            audioRecord = null
        }
    }

    /**
     * Stops the audio recording, flushes the final buffers, and returns the
     * entirely captured byte array (PCM bytes) meant for transmission.
     */
    suspend fun stopRecording(): ByteArray? = withContext(Dispatchers.IO) {
        if (!isRecording || audioRecord == null) {
            Timber.w("Cannot stop recording, AudioCapturer is not running.")
            return@withContext null
        }

        Timber.i("Stopping audio capture...")
        isRecording = false

        val outStream = ByteArrayOutputStream()
        val buffer = ByteArray(minBufferSize)

        try {
            // Read whatever is left in the buffer while state transitions to STOPPED
            audioRecord?.stop()
            while (true) {
                val bytesRead = audioRecord?.read(buffer, 0, buffer.size) ?: 0
                if (bytesRead > 0) {
                    outStream.write(buffer, 0, bytesRead)
                } else {
                    break
                }
            }
        } catch (e: Exception) {
            Timber.e(e, "Exception stopping record and reading final buffer")
        } finally {
            audioRecord?.release()
            audioRecord = null
        }

        val finalBytes = outStream.toByteArray()
        Timber.i("Audio capture completed. Total payload: \${finalBytes.size} bytes.")
        
        return@withContext if (finalBytes.isNotEmpty()) finalBytes else null
    }

    /**
     * To be called in a tight loop from a coroutine if streamingly sending chunks.
     * Currently not used if we implement simple Push-to-Talk (record all, then send).
     */
    fun readChunk(buffer: ByteArray): Int {
        return if (isRecording) {
            audioRecord?.read(buffer, 0, buffer.size) ?: 0
        } else {
            0
        }
    }
}
