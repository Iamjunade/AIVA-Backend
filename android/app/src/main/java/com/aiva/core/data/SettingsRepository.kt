package com.aiva.core.data

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import com.aiva.BuildConfig
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map

val Context.dataStore by preferencesDataStore(name = "settings")

class SettingsRepository(private val context: Context) {
    
    companion object {
        val SERVER_URL = stringPreferencesKey("server_url")
        val AUTH_TOKEN = stringPreferencesKey("auth_token")
    }

    val serverUrl: Flow<String> = context.dataStore.data
        .map { preferences ->
            // Use saved URL or fallback to Build Config default
            preferences[SERVER_URL] ?: BuildConfig.WS_URL
        }

    suspend fun saveServerUrl(url: String) {
        context.dataStore.edit { settings ->
            settings[SERVER_URL] = url
        }
    }
}
