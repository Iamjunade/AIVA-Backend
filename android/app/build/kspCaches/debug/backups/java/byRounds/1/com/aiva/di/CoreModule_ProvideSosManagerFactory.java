package com.aiva.di;

import android.content.Context;
import com.aiva.core.location.AivaLocationManager;
import com.aiva.core.sos.SosManager;
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
public final class CoreModule_ProvideSosManagerFactory implements Factory<SosManager> {
  private final Provider<Context> contextProvider;

  private final Provider<AivaLocationManager> locationManagerProvider;

  public CoreModule_ProvideSosManagerFactory(Provider<Context> contextProvider,
      Provider<AivaLocationManager> locationManagerProvider) {
    this.contextProvider = contextProvider;
    this.locationManagerProvider = locationManagerProvider;
  }

  @Override
  public SosManager get() {
    return provideSosManager(contextProvider.get(), locationManagerProvider.get());
  }

  public static CoreModule_ProvideSosManagerFactory create(Provider<Context> contextProvider,
      Provider<AivaLocationManager> locationManagerProvider) {
    return new CoreModule_ProvideSosManagerFactory(contextProvider, locationManagerProvider);
  }

  public static SosManager provideSosManager(Context context, AivaLocationManager locationManager) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideSosManager(context, locationManager));
  }
}
