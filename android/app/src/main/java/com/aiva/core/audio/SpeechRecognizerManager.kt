package com.aiva.core.audio

import android.content.Context
import android.content.Intent
import android.os.Bundle
import android.speech.RecognitionListener
import android.speech.RecognizerIntent
import android.speech.SpeechRecognizer
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import timber.log.Timber
import java.util.Locale

/**
 * On-device Speech-to-Text manager using Android's SpeechRecognizer.
 *
 * All speech recognition happens on the mobile device itself.
 * Results are emitted as text strings — no audio is sent over the network.
 *
 * Usage:
 *   1. Call startListening() when user taps the mic button
 *   2. Collect transcriptionResults to get recognized text
 *   3. SpeechRecognizer auto-stops on silence (endOfSpeech callback)
 */
class SpeechRecognizerManager(private val context: Context) {

    private var speechRecognizer: SpeechRecognizer? = null

    private val _isListening = MutableStateFlow(false)
    val isListening: StateFlow<Boolean> = _isListening.asStateFlow()

    private val _transcriptionResults = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val transcriptionResults: SharedFlow<String> = _transcriptionResults.asSharedFlow()

    private val _error = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val error: SharedFlow<String> = _error.asSharedFlow()

    private val recognizerIntent: Intent by lazy {
        Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH).apply {
            putExtra(
                RecognizerIntent.EXTRA_LANGUAGE_MODEL,
                RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
            )
            putExtra(RecognizerIntent.EXTRA_LANGUAGE, Locale.getDefault())
            putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS, true)
            putExtra(RecognizerIntent.EXTRA_MAX_RESULTS, 1)
            // Prefer offline recognition if available
            putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE, true)
            // Aggressively cut off listening when the user stops speaking
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_POSSIBLY_COMPLETE_SILENCE_LENGTH_MILLIS, 1000L)
            putExtra(RecognizerIntent.EXTRA_SPEECH_INPUT_MINIMUM_LENGTH_MILLIS, 1000L)
        }
    }

    private val listener = object : RecognitionListener {
        override fun onReadyForSpeech(params: Bundle?) {
            Timber.i("[Mobile STT] Ready for speech")
            _isListening.value = true
        }

        override fun onBeginningOfSpeech() {
            Timber.d("[Mobile STT] User started speaking")
        }

        override fun onRmsChanged(rmsdB: Float) {
            // Could be used for a visual audio level indicator
        }

        override fun onBufferReceived(buffer: ByteArray?) {}

        override fun onEndOfSpeech() {
            Timber.i("[Mobile STT] End of speech detected")
            _isListening.value = false
        }

        override fun onError(error: Int) {
            val errorMessage = when (error) {
                SpeechRecognizer.ERROR_NO_MATCH -> "No speech detected"
                SpeechRecognizer.ERROR_SPEECH_TIMEOUT -> "No speech input"
                SpeechRecognizer.ERROR_AUDIO -> "Audio recording error"
                SpeechRecognizer.ERROR_CLIENT -> "Client error"
                SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS -> "Microphone permission denied"
                SpeechRecognizer.ERROR_NETWORK -> "Network error (offline mode may not be available)"
                SpeechRecognizer.ERROR_NETWORK_TIMEOUT -> "Network timeout"
                SpeechRecognizer.ERROR_RECOGNIZER_BUSY -> "Recognizer busy"
                SpeechRecognizer.ERROR_SERVER -> "Server error"
                else -> "Unknown error ($error)"
            }
            Timber.w("[Mobile STT] Error: $errorMessage")
            _isListening.value = false
            _error.tryEmit(errorMessage)
        }

        override fun onResults(results: Bundle?) {
            val matches = results?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
            val bestResult = matches?.firstOrNull()

            if (!bestResult.isNullOrBlank()) {
                Timber.i("[Mobile STT] Final result: '$bestResult'")
                _transcriptionResults.tryEmit(bestResult)
            } else {
                Timber.w("[Mobile STT] No transcription result")
                _error.tryEmit("Could not understand speech")
            }
            _isListening.value = false
        }

        override fun onPartialResults(partialResults: Bundle?) {
            val partial = partialResults
                ?.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION)
                ?.firstOrNull()
            if (!partial.isNullOrBlank()) {
                Timber.d("[Mobile STT] Partial: '$partial'")
            }
        }

        override fun onEvent(eventType: Int, params: Bundle?) {}
    }

    /**
     * Initialize and start listening for speech.
     * Must be called from the Main thread (Android SpeechRecognizer requirement).
     */
    fun startListening() {
        if (_isListening.value) {
            Timber.w("[Mobile STT] Already listening, ignoring duplicate start")
            return
        }

        try {
            // Create a fresh recognizer each time (recommended by Android docs)
            speechRecognizer?.destroy()
            speechRecognizer = SpeechRecognizer.createSpeechRecognizer(context).also {
                it.setRecognitionListener(listener)
                it.startListening(recognizerIntent)
            }
            Timber.i("[Mobile STT] Started listening")
        } catch (e: Exception) {
            Timber.e(e, "[Mobile STT] Failed to start listening")
            _isListening.value = false
            _error.tryEmit("Failed to start speech recognition: ${e.message}")
        }
    }

    /**
     * Stop listening and cancel any in-progress recognition.
     */
    fun stopListening() {
        try {
            speechRecognizer?.stopListening()
            _isListening.value = false
            Timber.i("[Mobile STT] Stopped listening")
        } catch (e: Exception) {
            Timber.e(e, "[Mobile STT] Error stopping listener")
        }
    }

    /**
     * Release all resources. Call when the ViewModel is cleared.
     */
    fun destroy() {
        try {
            speechRecognizer?.destroy()
            speechRecognizer = null
            _isListening.value = false
            Timber.i("[Mobile STT] Destroyed")
        } catch (e: Exception) {
            Timber.e(e, "[Mobile STT] Error destroying recognizer")
        }
    }
}
