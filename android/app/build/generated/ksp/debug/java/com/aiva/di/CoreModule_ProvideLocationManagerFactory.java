package com.aiva.di;

import android.content.Context;
import com.aiva.core.location.AivaLocationManager;
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
public final class CoreModule_ProvideLocationManagerFactory implements Factory<AivaLocationManager> {
  private final Provider<Context> contextProvider;

  public CoreModule_ProvideLocationManagerFactory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public AivaLocationManager get() {
    return provideLocationManager(contextProvider.get());
  }

  public static CoreModule_ProvideLocationManagerFactory create(Provider<Context> contextProvider) {
    return new CoreModule_ProvideLocationManagerFactory(contextProvider);
  }

  public static AivaLocationManager provideLocationManager(Context context) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideLocationManager(context));
  }
}
