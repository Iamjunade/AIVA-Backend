package com.aiva.core.audio;

import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
import dagger.internal.QualifierMetadata;
import dagger.internal.ScopeMetadata;
import javax.annotation.processing.Generated;

@ScopeMetadata("javax.inject.Singleton")
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
public final class AudioCapturer_Factory implements Factory<AudioCapturer> {
  @Override
  public AudioCapturer get() {
    return newInstance();
  }

  public static AudioCapturer_Factory create() {
    return InstanceHolder.INSTANCE;
  }

  public static AudioCapturer newInstance() {
    return new AudioCapturer();
  }

  private static final class InstanceHolder {
    private static final AudioCapturer_Factory INSTANCE = new AudioCapturer_Factory();
  }
}
