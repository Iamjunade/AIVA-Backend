package com.aiva.di;

import android.content.Context;
import com.aiva.core.audio.SpeechRecognizerManager;
import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
import dagger.internal.Preconditions;
import dagger.internal.QualifierMetadata;
import dagger.internal.ScopeMetadata;
import javax.annotation.processing.Generated;
import javax.inject.Provider;

@ScopeMetadata("javax.inject.Singleton")
@QualifierMetadata("dagger.hilt.android.qualifiers.ApplicationContext")
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
public final class CoreModule_ProvideSpeechRecognizerManagerFactory implements Factory<SpeechRecognizerManager> {
  private final Provider<Context> contextProvider;

  public CoreModule_ProvideSpeechRecognizerManagerFactory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public SpeechRecognizerManager get() {
    return provideSpeechRecognizerManager(contextProvider.get());
  }

  public static CoreModule_ProvideSpeechRecognizerManagerFactory create(
      Provider<Context> contextProvider) {
    return new CoreModule_ProvideSpeechRecognizerManagerFactory(contextProvider);
  }

  public static SpeechRecognizerManager provideSpeechRecognizerManager(Context context) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideSpeechRecognizerManager(context));
  }
}
