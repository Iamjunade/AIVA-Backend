package com.aiva.feature.vision;

import com.aiva.core.audio.SpeechRecognizerManager;
import com.aiva.core.camera.CameraManager;
import com.aiva.core.connection.WebSocketManager;
import com.aiva.core.protocol.FramePacketizer;
import com.aiva.core.tts.TTSManager;
import com.aiva.data.repository.SettingsRepository;
import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
import dagger.internal.QualifierMetadata;
import dagger.internal.ScopeMetadata;
import javax.annotation.processing.Generated;
import javax.inject.Provider;

@ScopeMetadata
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
public final class VisionViewModel_Factory implements Factory<VisionViewModel> {
  private final Provider<WebSocketManager> webSocketManagerProvider;

  private final Provider<CameraManager> cameraManagerProvider;

  private final Provider<SpeechRecognizerManager> speechRecognizerManagerProvider;

  private final Provider<TTSManager> ttsManagerProvider;

  private final Provider<FramePacketizer> packetizerProvider;

  private final Provider<SettingsRepository> settingsRepositoryProvider;

  public VisionViewModel_Factory(Provider<WebSocketManager> webSocketManagerProvider,
      Provider<CameraManager> cameraManagerProvider,
      Provider<SpeechRecognizerManager> speechRecognizerManagerProvider,
      Provider<TTSManager> ttsManagerProvider, Provider<FramePacketizer> packetizerProvider,
      Provider<SettingsRepository> settingsRepositoryProvider) {
    this.webSocketManagerProvider = webSocketManagerProvider;
    this.cameraManagerProvider = cameraManagerProvider;
    this.speechRecognizerManagerProvider = speechRecognizerManagerProvider;
    this.ttsManagerProvider = ttsManagerProvider;
    this.packetizerProvider = packetizerProvider;
    this.settingsRepositoryProvider = settingsRepositoryProvider;
  }

  @Override
  public VisionViewModel get() {
    return newInstance(webSocketManagerProvider.get(), cameraManagerProvider.get(), speechRecognizerManagerProvider.get(), ttsManagerProvider.get(), packetizerProvider.get(), settingsRepositoryProvider.get());
  }

  public static VisionViewModel_Factory create(Provider<WebSocketManager> webSocketManagerProvider,
      Provider<CameraManager> cameraManagerProvider,
      Provider<SpeechRecognizerManager> speechRecognizerManagerProvider,
      Provider<TTSManager> ttsManagerProvider, Provider<FramePacketizer> packetizerProvider,
      Provider<SettingsRepository> settingsRepositoryProvider) {
    return new VisionViewModel_Factory(webSocketManagerProvider, cameraManagerProvider, speechRecognizerManagerProvider, ttsManagerProvider, packetizerProvider, settingsRepositoryProvider);
  }

  public static VisionViewModel newInstance(WebSocketManager webSocketManager,
      CameraManager cameraManager, SpeechRecognizerManager speechRecognizerManager,
      TTSManager ttsManager, FramePacketizer packetizer, SettingsRepository settingsRepository) {
    return new VisionViewModel(webSocketManager, cameraManager, speechRecognizerManager, ttsManager, packetizer, settingsRepository);
  }
}
