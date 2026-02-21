package com.aiva.core.connection

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import com.aiva.BuildConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import timber.log.Timber
import java.io.IOException
import java.util.concurrent.TimeUnit

/**
 * AIVA — JWT Manager
 *
 * Handles secure storage and lifecycle of JWT access tokens.
 *
 * Uses EncryptedSharedPreferences for storage.
 * Fetches initial token using the legacy AUTH_TOKEN (master key).
 * Refreshes tokens automatically when expired.
 */
class JwtTokenManager(context: Context) {

    private val masterKey = MasterKey.Builder(context)
        .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
        .build()

    private val sharedPreferences = EncryptedSharedPreferences.create(
        context,
        "aiva_secure_prefs",
        masterKey,
        EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
        EncryptedSharedPreferences.ValueEncryptionScheme.AES256_GCM
    )

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    companion object {
        private const val KEY_JWT = "jwt_access_token"
        private const val KEY_EXPIRY = "jwt_expiry_timestamp"
        private val JSON = "application/json; charset=utf-8".toMediaType()
    }

    /**
     * Get a valid JWT access token.
     * Refreshes automatically if expired or missing.
     *
     * @param serverUrl Base URL of the server (e.g. "http://192.168.1.100:8765")
     * @return Valid JWT string, or null if fetch failed
     */
    suspend fun getToken(serverUrl: String): String? {
        val cachedToken = sharedPreferences.getString(KEY_JWT, null)
        val expiry = sharedPreferences.getLong(KEY_EXPIRY, 0)
        val now = System.currentTimeMillis()

        // Buffer: refresh 5 minutes before actual expiry
        if (cachedToken != null && now < expiry - 300_000) {
            return cachedToken
        }

        Timber.i("Token expired or missing. Fetching new one...")
        return fetchNewToken(serverUrl, cachedToken)
    }

    private suspend fun fetchNewToken(serverUrl: String, oldToken: String?): String? = withContext(Dispatchers.IO) {
        // Try refresh first if we have an old token
        if (oldToken != null) {
            val refreshed = performRequest("$serverUrl/auth/refresh", oldToken)
            if (refreshed != null) return@withContext refreshed
        }

        // Fallback: Get fresh token using Master Key (legacy AUTH_TOKEN)
        performRequest("$serverUrl/auth/token", BuildConfig.AUTH_TOKEN)
    }

    private fun performRequest(endpoint: String, authToken: String): String? {
        try {
            val request = Request.Builder()
                .url(endpoint)
                .post("".toRequestBody(JSON)) // Empty body
                .addHeader("Authorization", "Bearer $authToken")
                .build()

            client.newCall(request).execute().use { response ->
                if (!response.isSuccessful) {
                    Timber.w("Auth request failed: ${response.code} ${response.message}")
                    return null
                }

                val json = response.body?.string() ?: return null
                val data = JSONObject(json)
                val token = data.getString("access_token")
                val expiresInSeconds = data.getLong("expires_in") // Valid seconds from now

                saveToken(token, expiresInSeconds)
                return token
            }
        } catch (e: Exception) {
            Timber.e(e, "Failed to fetch token from $endpoint")
            return null
        }
    }

    private fun saveToken(token: String, expiresInSeconds: Long) {
        val expiryMs = System.currentTimeMillis() + (expiresInSeconds * 1000)
        sharedPreferences.edit()
            .putString(KEY_JWT, token)
            .putLong(KEY_EXPIRY, expiryMs)
            .apply()
        Timber.i("New JWT cached. Expires in ${expiresInSeconds / 3600}h")
    }

    fun clearToken() {
        sharedPreferences.edit().clear().apply()
    }
}
