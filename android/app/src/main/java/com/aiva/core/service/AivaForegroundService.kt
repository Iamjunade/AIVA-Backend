package com.aiva.core.service

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.NotificationCompat
import com.aiva.R

import androidx.lifecycle.LifecycleService
import com.aiva.core.camera.CameraManager
import com.aiva.core.connection.WebSocketManager
import com.aiva.core.location.AivaLocationManager
import com.aiva.core.sos.SosManager
import com.aiva.core.tts.TTSManager
import com.aiva.core.tts.VoicePriority
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject

@AndroidEntryPoint
class AivaForegroundService : LifecycleService() {

    @Inject lateinit var webSocketManager: WebSocketManager
    @Inject lateinit var sosManager: SosManager
    @Inject lateinit var locationManager: AivaLocationManager
    @Inject lateinit var ttsManager: TTSManager
    @Inject lateinit var cameraManager: CameraManager

    private val serviceScope = CoroutineScope(Dispatchers.Main + SupervisorJob())

    override fun onCreate() {
        super.onCreate()
        
        val notification = createNotification()
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            startForeground(
                1, 
                notification, 
                ServiceInfo.FOREGROUND_SERVICE_TYPE_CAMERA or ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE
            )
        } else {
            startForeground(1, notification)
        }

        startCommandListener()
        
        // Bind Camera to Service Lifecycle
        cameraManager.startCamera(this)
    }

    private fun startCommandListener() {
        serviceScope.launch {
            webSocketManager.commandEvents.collect { command ->
                when (command.action) {
                    "SOS" -> {
                        Timber.w("Executing SOS Command")
                        sosManager.triggerSos()
                        ttsManager.speak("Emergency SOS triggered. Sending location to contacts.", VoicePriority.DANGER)
                    }
                    "LOCATION" -> {
                        Timber.i("Executing Location Command")
                        val location = locationManager.getCurrentLocation()
                        if (location != null) {
                            val text = "You are at coordinates: ${location.latitude}, ${location.longitude}"
                            ttsManager.speak(text, VoicePriority.INFO)
                        } else {
                            ttsManager.speak("Unable to determine location.", VoicePriority.INFO)
                        }
                    }
                    else -> Timber.d("Unknown command action: ${command.action}")
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        super.onStartCommand(intent, flags, startId)
        return START_STICKY
    }

    private fun createNotification(): Notification {
        val channelId = "aiva_service_channel"
        val channelName = "AIVA Service"
        
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                channelId, channelName, NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(channel)
        }

        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("AIVA is Active")
            .setContentText("Monitoring surroundings for obstacles")
            .setSmallIcon(android.R.drawable.ic_menu_camera)
            .build()
    }
}
