package com.aiva.core.service;

import com.aiva.core.camera.CameraManager;
import com.aiva.core.connection.WebSocketManager;
import com.aiva.core.location.AivaLocationManager;
import com.aiva.core.sos.SosManager;
import com.aiva.core.tts.TTSManager;
import dagger.MembersInjector;
import dagger.internal.DaggerGenerated;
import dagger.internal.InjectedFieldSignature;
import dagger.internal.QualifierMetadata;
import javax.annotation.processing.Generated;
import javax.inject.Provider;

@QualifierMetadata
@DaggerGenerated
@Generated(
    value = "dagger.internal.codegen.ComponentProcessor",
    comments = "https://dagger.dev"
)
@SuppressWarnings({
    "unchecked",
    "rawtypes",
    "KotlinInternal",
    "KotlinInternalInJava"
})
public final class AivaForegroundService_MembersInjector implements MembersInjector<AivaForegroundService> {
  private final Provider<WebSocketManager> webSocketManagerProvider;

  private final Provider<SosManager> sosManagerProvider;

  private final Provider<AivaLocationManager> locationManagerProvider;

  private final Provider<TTSManager> ttsManagerProvider;

  private final Provider<CameraManager> cameraManagerProvider;

  public AivaForegroundService_MembersInjector(Provider<WebSocketManager> webSocketManagerProvider,
      Provider<SosManager> sosManagerProvider,
      Provider<AivaLocationManager> locationManagerProvider,
      Provider<TTSManager> ttsManagerProvider, Provider<CameraManager> cameraManagerProvider) {
    this.webSocketManagerProvider = webSocketManagerProvider;
    this.sosManagerProvider = sosManagerProvider;
    this.locationManagerProvider = locationManagerProvider;
    this.ttsManagerProvider = ttsManagerProvider;
    this.cameraManagerProvider = cameraManagerProvider;
  }

  public static MembersInjector<AivaForegroundService> create(
      Provider<WebSocketManager> webSocketManagerProvider, Provider<SosManager> sosManagerProvider,
      Provider<AivaLocationManager> locationManagerProvider,
      Provider<TTSManager> ttsManagerProvider, Provider<CameraManager> cameraManagerProvider) {
    return new AivaForegroundService_MembersInjector(webSocketManagerProvider, sosManagerProvider, locationManagerProvider, ttsManagerProvider, cameraManagerProvider);
  }

  @Override
  public void injectMembers(AivaForegroundService instance) {
    injectWebSocketManager(instance, webSocketManagerProvider.get());
    injectSosManager(instance, sosManagerProvider.get());
    injectLocationManager(instance, locationManagerProvider.get());
    injectTtsManager(instance, ttsManagerProvider.get());
    injectCameraManager(instance, cameraManagerProvider.get());
  }

  @InjectedFieldSignature("com.aiva.core.service.AivaForegroundService.webSocketManager")
  public static void injectWebSocketManager(AivaForegroundService instance,
      WebSocketManager webSocketManager) {
    instance.webSocketManager = webSocketManager;
  }

  @InjectedFieldSignature("com.aiva.core.service.AivaForegroundService.sosManager")
  public static void injectSosManager(AivaForegroundService instance, SosManager sosManager) {
    instance.sosManager = sosManager;
  }

  @InjectedFieldSignature("com.aiva.core.service.AivaForegroundService.locationManager")
  public static void injectLocationManager(AivaForegroundService instance,
      AivaLocationManager locationManager) {
    instance.locationManager = locationManager;
  }

  @InjectedFieldSignature("com.aiva.core.service.AivaForegroundService.ttsManager")
  public static void injectTtsManager(AivaForegroundService instance, TTSManager ttsManager) {
    instance.ttsManager = ttsManager;
  }

  @InjectedFieldSignature("com.aiva.core.service.AivaForegroundService.cameraManager")
  public static void injectCameraManager(AivaForegroundService instance,
      CameraManager cameraManager) {
    instance.cameraManager = cameraManager;
  }
}
