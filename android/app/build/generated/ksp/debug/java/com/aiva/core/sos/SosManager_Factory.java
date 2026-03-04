package com.aiva.core.sos;

import android.content.Context;
import com.aiva.core.location.AivaLocationManager;
import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
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
public final class SosManager_Factory implements Factory<SosManager> {
  private final Provider<Context> contextProvider;

  private final Provider<AivaLocationManager> locationManagerProvider;

  public SosManager_Factory(Provider<Context> contextProvider,
      Provider<AivaLocationManager> locationManagerProvider) {
    this.contextProvider = contextProvider;
    this.locationManagerProvider = locationManagerProvider;
  }

  @Override
  public SosManager get() {
    return newInstance(contextProvider.get(), locationManagerProvider.get());
  }

  public static SosManager_Factory create(Provider<Context> contextProvider,
      Provider<AivaLocationManager> locationManagerProvider) {
    return new SosManager_Factory(contextProvider, locationManagerProvider);
  }

  public static SosManager newInstance(Context context, AivaLocationManager locationManager) {
    return new SosManager(context, locationManager);
  }
}
