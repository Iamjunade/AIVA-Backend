package com.aiva.core.connection

import com.aiva.core.protocol.ServerMessage
import com.aiva.util.BackoffPolicy
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharedFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asSharedFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.Response
import okhttp3.WebSocket
import okhttp3.WebSocketListener
import okio.ByteString.Companion.toByteString
import timber.log.Timber
import java.util.concurrent.TimeUnit

class WebSocketManager(
    private val jwtTokenManager: JwtTokenManager
) {

    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(30, TimeUnit.SECONDS)
        .writeTimeout(15, TimeUnit.SECONDS)
        .pingInterval(20, TimeUnit.SECONDS)  // Match server's ping_interval
        .build()

    private val moshi = Moshi.Builder()
        .add(KotlinJsonAdapterFactory())
        .build()
    private val adapter = moshi.adapter(ServerMessage::class.java)

    private val _connectionState = MutableStateFlow(ConnectionState.DISCONNECTED)
    val connectionState: StateFlow<ConnectionState> = _connectionState.asStateFlow()

    private val _serverEvents = MutableSharedFlow<ServerMessage>()
    val serverEvents: SharedFlow<ServerMessage> = _serverEvents.asSharedFlow()

    private val _commandEvents = MutableSharedFlow<ServerMessage>()
    val commandEvents: SharedFlow<ServerMessage> = _commandEvents.asSharedFlow()

    private var webSocket: WebSocket? = null
    private val backoff = BackoffPolicy()
    private var isIntentionalDisconnect = false
    private var currentUrl: String? = null

    // Telemetry tracking
    var framesDropped = 0
        private set

    fun connect(url: String) {
        if (_connectionState.value == ConnectionState.CONNECTED || _connectionState.value == ConnectionState.CONNECTING) return
        
        currentUrl = url
        isIntentionalDisconnect = false
        _connectionState.value = ConnectionState.CONNECTING
        attemptConnection()
    }

    private fun attemptConnection() {
        val url = currentUrl ?: return
        scope.launch {
            try {
                // Convert WS URL to HTTP base URL for auth
                // ws://1.2.3.4:8765/ws -> http://1.2.3.4:8765
                val httpUrl = url.replace("ws://", "http://")
                    .replace("wss://", "https://")
                    .replace("/ws", "")
                
                // Get valid JWT (handles refresh or fetch via master token)
                val token = jwtTokenManager.getToken(httpUrl)
                
                if (token == null) {
                    Timber.e("Failed to obtain JWT token")
                    handleConnectionFailure()
                    return@launch
                }

                val request = Request.Builder()
                    .url(url)
                    .addHeader("Authorization", "Bearer $token")
                    .build()

                Timber.i("Connecting to $url with JWT")
                webSocket = client.newWebSocket(request, SocketListener())
            } catch (e: Exception) {
                Timber.e(e, "Connection attempt failed")
                handleConnectionFailure()
            }
        }
    }

    fun disconnect() {
        isIntentionalDisconnect = true
        webSocket?.close(1000, "User Disconnect")
        webSocket = null
        _connectionState.value = ConnectionState.DISCONNECTED
    }

    fun sendFrame(frameData: ByteArray) {
        if (_connectionState.value != ConnectionState.CONNECTED) {
            framesDropped++
            return
        }

        webSocket?.send(frameData.toByteString())
    }

    private fun handleConnectionFailure(forceClearToken: Boolean = false) {
        if (isIntentionalDisconnect) return

        if (forceClearToken) {
            jwtTokenManager.clearToken()
        }

        _connectionState.value = ConnectionState.RECONNECTING
        
        val delayMs = backoff.nextBackoff()
        Timber.w("Connection lost. Reconnecting in ${delayMs}ms")

        scope.launch {
            delay(delayMs)
            attemptConnection()
        }
    }

    private inner class SocketListener : WebSocketListener() {
        override fun onOpen(webSocket: WebSocket, response: Response) {
            Timber.i("WebSocket Connected")
            _connectionState.value = ConnectionState.CONNECTED
            backoff.reset()
        }

        override fun onMessage(webSocket: WebSocket, text: String) {
            try {
                val message = adapter.fromJson(text)
                if (message != null) {
                    if (message.type == "command") {
                        Timber.w("!!! RECEIVED HIGH PRIORITY COMMAND: ${message.action} !!!")
                        scope.launch { _commandEvents.emit(message) }
                    } else {
                        scope.launch { _serverEvents.emit(message) }
                    }
                }
            } catch (e: Exception) {
                Timber.e(e, "Failed to parse message: $text")
            }
        }

        override fun onClosing(webSocket: WebSocket, code: Int, reason: String) {
            Timber.i("WebSocket Closing: $code / $reason")
            _connectionState.value = ConnectionState.DISCONNECTED
        }

        override fun onClosed(webSocket: WebSocket, code: Int, reason: String) {
            Timber.i("WebSocket Closed")
            if (!isIntentionalDisconnect) {
                handleConnectionFailure()
            }
        }

        override fun onFailure(webSocket: WebSocket, t: Throwable, response: Response?) {
            Timber.e(t, "WebSocket Failure [${t.javaClass.simpleName}]: ${t.message}")
            var isAuthFailure = false
            response?.let { resp ->
                Timber.e("  HTTP ${resp.code}: ${resp.message}")
                if (resp.code == 401) {
                    isAuthFailure = true
                    Timber.w("  Auth failure (401) — clearing token and retrying")
                }
                try { Timber.e("  Body: ${resp.body?.string()?.take(500)}") } catch (_: Exception) {}
            } ?: Timber.e("  No HTTP response (transport-level failure)")
            
            handleConnectionFailure(forceClearToken = isAuthFailure)
        }
    }
}
