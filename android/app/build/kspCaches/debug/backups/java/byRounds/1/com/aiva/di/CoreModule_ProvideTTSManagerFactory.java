package com.aiva.di;

import android.content.Context;
import com.aiva.core.tts.TTSManager;
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
public final class CoreModule_ProvideTTSManagerFactory implements Factory<TTSManager> {
  private final Provider<Context> contextProvider;

  public CoreModule_ProvideTTSManagerFactory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public TTSManager get() {
    return provideTTSManager(contextProvider.get());
  }

  public static CoreModule_ProvideTTSManagerFactory create(Provider<Context> contextProvider) {
    return new CoreModule_ProvideTTSManagerFactory(contextProvider);
  }

  public static TTSManager provideTTSManager(Context context) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideTTSManager(context));
  }
}
