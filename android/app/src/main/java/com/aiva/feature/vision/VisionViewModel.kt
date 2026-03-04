package com.aiva.feature.vision

import androidx.lifecycle.LifecycleOwner
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import androidx.camera.core.Preview
import com.aiva.core.audio.SpeechRecognizerManager
import com.aiva.core.camera.CameraManager
import com.aiva.core.connection.ConnectionState
import com.aiva.core.connection.WebSocketManager
import com.aiva.core.protocol.FramePacketizer
import com.aiva.core.tts.TTSManager
import com.aiva.core.tts.VoicePriority
import com.aiva.data.repository.SettingsRepository
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.collectLatest
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

@HiltViewModel
class VisionViewModel @Inject constructor(
    private val webSocketManager: WebSocketManager,
    private val cameraManager: CameraManager,
    private val speechRecognizerManager: SpeechRecognizerManager,
    private val ttsManager: TTSManager,
    private val packetizer: FramePacketizer,
    private val settingsRepository: SettingsRepository
) : ViewModel() {

    private val _uiState = MutableStateFlow(VisionUiState())
    val uiState: StateFlow<VisionUiState> = _uiState.asStateFlow()

    init {
        // Collect Settings & Connect
        viewModelScope.launch {
            settingsRepository.serverUrl.collectLatest { url ->
                Timber.i("Configuration change: Connecting to $url")
                webSocketManager.disconnect()
                webSocketManager.connect(url)
            }
        }
        // Collect Connection State
        viewModelScope.launch {
            webSocketManager.connectionState.collectLatest { state ->
                _uiState.value = _uiState.value.copy(connectionState = state.name)
                
                if (state == ConnectionState.DISCONNECTED || state == ConnectionState.FAILED) {
                    ttsManager.speak("Connection lost", VoicePriority.CAUTION)
                } else if (state == ConnectionState.CONNECTED) {
                    ttsManager.speak("Connected", VoicePriority.INFO)
                    packetizer.reset()
                }
            }
        }

        // Collect Server Events
        viewModelScope.launch {
            webSocketManager.serverEvents.collect { msg ->
                // Update Latency & Stats
                val latency = msg.latencyMs ?: 0
                val fid = msg.frameId ?: 0
                
                // Process Warnings
                msg.warnings?.firstOrNull()?.let { warning ->
                    val priority = when (warning.priority.lowercase()) {
                        "danger" -> VoicePriority.DANGER
                        "caution" -> VoicePriority.CAUTION
                        else -> VoicePriority.INFO
                    }
                    
                    val text = "${warning.action} ${warning.objectName}"
                    ttsManager.speak(text, priority)
                    
                    _uiState.value = _uiState.value.copy(
                        warningLevel = warning.priority.uppercase(),
                        lastAction = warning.action
                    )
                } ?: run {
                    _uiState.value = _uiState.value.copy(warningLevel = "NONE")
                }

                // OCR
                msg.ocrText?.let { ttsManager.speak("Reading: $it", VoicePriority.INFO) }

                _uiState.value = _uiState.value.copy(
                    latencyMs = latency,
                    frameId = fid,
                    droppedFrames = webSocketManager.framesDropped
                )
            }
        }

        // Collect Speech Events (AIVA Voice Responses — spoken on the phone)
        viewModelScope.launch {
            webSocketManager.speechEvents.collect { msg ->
                msg.text?.let { text ->
                    Timber.i("AIVA Speaking: $text")
                    ttsManager.speak(text, VoicePriority.INFO)
                }
            }
        }

        // Collect on-device STT results → send as text query to backend
        viewModelScope.launch {
            speechRecognizerManager.transcriptionResults.collect { text ->
                Timber.i("[Mobile STT] Transcribed: '$text'")
                _uiState.update { it.copy(lastTranscription = text, isListening = false) }

                // Pack recognized text and send to backend
                val packet = packetizer.packTextQuery(text)
                webSocketManager.sendFrame(packet)
                Timber.i("Sent text query to backend: '$text' (${packet.size} bytes)")
            }
        }

        // Collect STT listening state
        viewModelScope.launch {
            speechRecognizerManager.isListening.collect { listening ->
                _uiState.update { it.copy(isListening = listening) }
            }
        }

        // Collect STT errors
        viewModelScope.launch {
            speechRecognizerManager.error.collect { errorMsg ->
                Timber.w("STT Error: $errorMsg")
                _uiState.update { it.copy(isListening = false) }
                ttsManager.speak(errorMsg, VoicePriority.INFO)
            }
        }
    }

    fun startCamera(lifecycleOwner: LifecycleOwner) {
        cameraManager.startCamera(lifecycleOwner)
        _uiState.update { it.copy(isStreaming = true) }
        
        // Pipeline: Camera -> Packetizer -> WebSocket
        viewModelScope.launch(Dispatchers.Default) {
            cameraManager.frameFlow.collectLatest { jpegBytes ->
                // Check if streaming is actually enabled
                if (_uiState.value.isStreaming) {
                    // Packetize (BigEndian, Timestamp) - Non-blocking
                    val packet = packetizer.pack(jpegBytes)
                    
                    // Send (Drop if full/disconnected)
                    webSocketManager.sendFrame(packet)
                }
            }
        }
    }
    
    fun stopCamera() {
        //cameraManager.stopCamera()
        _uiState.update { it.copy(isStreaming = false) }
    }
    
    fun toggleStreaming(lifecycleOwner: LifecycleOwner) {
        if (_uiState.value.isStreaming) {
            stopCamera()
        } else {
            startCamera(lifecycleOwner)
        }
    }

    fun saveServerUrl(url: String) {
        viewModelScope.launch {
            settingsRepository.saveServerUrl(url)
        }
    }

    fun setSurfaceProvider(provider: Preview.SurfaceProvider) {
        cameraManager.surfaceProvider = provider
    }

    /**
     * Start on-device speech recognition.
     * Tap once to start — SpeechRecognizer auto-stops on silence.
     * Must be called from Main thread.
     */
    fun startVoiceCommand() {
        if (_uiState.value.isListening) {
            // Already listening, stop it
            speechRecognizerManager.stopListening()
            _uiState.update { it.copy(isListening = false) }
            return
        }
        _uiState.update { it.copy(isListening = true, lastTranscription = "") }
        speechRecognizerManager.startListening()
    }

    override fun onCleared() {
        super.onCleared()
        webSocketManager.disconnect()
        speechRecognizerManager.destroy()
        ttsManager.shutdown()
    }
}
