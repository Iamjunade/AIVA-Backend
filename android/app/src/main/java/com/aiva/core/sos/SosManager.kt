package com.aiva.core.sos

import android.content.Context
import android.telephony.SmsManager
import com.aiva.core.location.AivaLocationManager
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import timber.log.Timber
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class SosManager @Inject constructor(
    @ApplicationContext private val context: Context,
    private val locationManager: AivaLocationManager
) {

    // TODO: Load from user preferences/DataStore
    private val emergencyContacts = listOf("5551234567") 

    fun triggerSos() {
        Timber.w("!!! SOS TRIGGERED !!!")
        CoroutineScope(Dispatchers.IO).launch {
            try {
                // 1. Get Location (Best effort)
                val location = locationManager.getCurrentLocation() 
                    ?: locationManager.getLastKnownLocation()

                // 2. Format Map Link
                val mapLink = if (location != null) {
                    "http://maps.google.com/maps?q=${location.latitude},${location.longitude}"
                } else {
                    "Location unavailable"
                }

                val message = "SOS! I need help. My location: $mapLink"

                // 3. Send SMS
                sendSmsToContacts(message)

            } catch (e: Exception) {
                Timber.e(e, "SOS Failed")
            }
        }
    }

    private fun sendSmsToContacts(message: String) {
        val smsManager = context.getSystemService(SmsManager::class.java)
        
        emergencyContacts.forEach { phone ->
            try {
                smsManager.sendTextMessage(phone, null, message, null, null)
                Timber.i("SOS sent to $phone")
            } catch (e: Exception) {
                Timber.e(e, "Failed to send SOS to $phone")
            }
        }
    }
}
