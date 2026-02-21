package com.aiva.core.protocol

import android.os.SystemClock
import java.nio.ByteBuffer
import java.nio.ByteOrder

class FramePacketizer {
    
    companion object {
        const val VERSION: Byte = 0x01
        const val TYPE_VIDEO: Byte = 0x01
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

    fun reset() {
        frameIdCount = 0
    }
}
