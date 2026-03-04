package com.aiva.core.protocol

import android.os.SystemClock
import java.nio.ByteBuffer
import java.nio.ByteOrder

class FramePacketizer {
    
    companion object {
        const val VERSION: Byte = 0x01
        const val TYPE_VIDEO: Byte = 0x01
        const val TYPE_AUDIO: Byte = 0x04
        const val TYPE_TEXT_QUERY: Byte = 0x05
        const val HEADER_SIZE = 10
    }

    private var frameIdCount = 0

    fun pack(jpeg: ByteArray): ByteArray {
        val timestamp = SystemClock.elapsedRealtime().toInt()
        val frameId = ++frameIdCount

        return ByteBuffer.allocate(HEADER_SIZE + jpeg.size)
            .order(ByteOrder.BIG_ENDIAN)
            .put(VERSION)
            .put(TYPE_VIDEO)
            .putInt(frameId)
            .putInt(timestamp)
            .put(jpeg)
            .array()
    }
    
    fun packAudio(pcmBytes: ByteArray): ByteArray {
        val timestamp = SystemClock.elapsedRealtime().toInt()
        val frameId = ++frameIdCount

        return ByteBuffer.allocate(HEADER_SIZE + pcmBytes.size)
            .order(ByteOrder.BIG_ENDIAN)
            .put(VERSION)
            .put(TYPE_AUDIO)
            .putInt(frameId)
            .putInt(timestamp)
            .put(pcmBytes)
            .array()
    }

    /**
     * Pack a pre-transcribed text query for the backend.
     * The backend will skip STT and process the text directly.
     */
    fun packTextQuery(text: String): ByteArray {
        val textBytes = text.toByteArray(Charsets.UTF_8)
        val timestamp = SystemClock.elapsedRealtime().toInt()
        val frameId = ++frameIdCount

        return ByteBuffer.allocate(HEADER_SIZE + textBytes.size)
            .order(ByteOrder.BIG_ENDIAN)
            .put(VERSION)
            .put(TYPE_TEXT_QUERY)
            .putInt(frameId)
            .putInt(timestamp)
            .put(textBytes)
            .array()
    }

    fun reset() {
        frameIdCount = 0
    }
}
