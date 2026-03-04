package com.aiva.di

import android.content.Context
import com.aiva.core.audio.SpeechRecognizerManager
import com.aiva.core.camera.CameraManager
import com.aiva.core.connection.JwtTokenManager
import com.aiva.core.connection.WebSocketManager
import com.aiva.core.location.AivaLocationManager
import com.aiva.core.protocol.FramePacketizer
import com.aiva.core.sos.SosManager
import com.aiva.core.tts.TTSManager
import dagger.Module
import dagger.Provides
import dagger.hilt.InstallIn
import dagger.hilt.android.qualifiers.ApplicationContext
import dagger.hilt.components.SingletonComponent
import javax.inject.Singleton

@Module
@InstallIn(SingletonComponent::class)
object CoreModule {

    @Provides
    @Singleton
    fun provideCameraManager(@ApplicationContext context: Context): CameraManager {
        return CameraManager(context)
    }

    @Provides
    @Singleton
    fun provideTTSManager(@ApplicationContext context: Context): TTSManager {
        return TTSManager(context)
    }

    @Provides
    @Singleton
    fun provideSpeechRecognizerManager(@ApplicationContext context: Context): SpeechRecognizerManager {
        return SpeechRecognizerManager(context)
    }

    @Provides
    @Singleton
    fun provideJwtTokenManager(@ApplicationContext context: Context): JwtTokenManager {
        return JwtTokenManager(context)
    }

    @Provides
    @Singleton
    fun provideWebSocketManager(jwtTokenManager: JwtTokenManager): WebSocketManager {
        return WebSocketManager(jwtTokenManager)
    }

    @Provides
    @Singleton
    fun provideFramePacketizer(): FramePacketizer {
        return FramePacketizer()
    }

    @Provides
    @Singleton
    fun provideLocationManager(@ApplicationContext context: Context): AivaLocationManager {
        return AivaLocationManager(context)
    }

    @Provides
    @Singleton
    fun provideSosManager(
        @ApplicationContext context: Context,
        locationManager: AivaLocationManager
    ): SosManager {
        return SosManager(context, locationManager)
    }
}

