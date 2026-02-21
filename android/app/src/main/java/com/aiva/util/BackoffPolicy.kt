package com.aiva.util

import kotlin.math.min
import kotlin.math.pow
import kotlin.random.Random

class BackoffPolicy(
    private val initialDelayMs: Long = 1000,
    private val maxDelayMs: Long = 30000,
    private val factor: Double = 2.0,
    private val jitter: Double = 0.1
) {
    private var attempt = 0

    fun nextBackoff(): Long {
        val delay = initialDelayMs * factor.pow(attempt.toDouble())
        attempt++
        
        val jitterMs = (delay * jitter * Random.nextDouble(-1.0, 1.0)).toLong()
        return min(delay.toLong() + jitterMs, maxDelayMs)
    }

    fun reset() {
        attempt = 0
    }
}
