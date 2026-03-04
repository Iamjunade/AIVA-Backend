package com.aiva.feature.vision

data class VisionUiState(
    val connectionState: String = "DISCONNECTED",
    val latencyMs: Int = 0,
    val frameId: Int = 0,
    val droppedFrames: Int = 0,
    val warningLevel: String = "NONE",
    val lastAction: String = "",
    val isStreaming: Boolean = false,
    val isMicRecording: Boolean = false,
    val isListening: Boolean = false,
    val lastTranscription: String = ""
)
