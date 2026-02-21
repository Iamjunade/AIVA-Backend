package com.aiva.core.protocol

import com.squareup.moshi.Json
import com.squareup.moshi.JsonClass

@JsonClass(generateAdapter = true)
data class ServerMessage(
    @Json(name = "type") val type: String,
    @Json(name = "frame_id") val frameId: Int? = null,
    @Json(name = "timestamp_ms") val timestampMs: Long? = null,
    @Json(name = "latency_ms") val latencyMs: Int? = null,
    @Json(name = "detections") val detections: List<Detection>? = null,
    @Json(name = "warnings") val warnings: List<Warning>? = null,
    @Json(name = "ocr_text") val ocrText: String? = null,
    @Json(name = "models_loaded") val modelsLoaded: Boolean? = null,
    @Json(name = "code") val errorCode: String? = null,
    @Json(name = "message") val errorMessage: String? = null,
    @Json(name = "action") val action: String? = null,
    @Json(name = "params") val params: Map<String, Any>? = null
)

@JsonClass(generateAdapter = true)
data class Detection(
    @Json(name = "class") val className: String,
    @Json(name = "confidence") val confidence: Float,
    @Json(name = "distance_m") val distanceM: Float?,
    @Json(name = "direction") val direction: String?
)

@JsonClass(generateAdapter = true)
data class Warning(
    @Json(name = "action") val action: String, // STOP, CAUTION, INFO
    @Json(name = "object") val objectName: String,
    @Json(name = "priority") val priority: String,
    @Json(name = "zone") val zone: String,
    @Json(name = "distance") val distance: Float?
)
