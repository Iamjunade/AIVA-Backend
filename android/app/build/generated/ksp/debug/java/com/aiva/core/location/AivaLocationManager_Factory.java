package com.aiva.core.location;

import android.content.Context;
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
public final class AivaLocationManager_Factory implements Factory<AivaLocationManager> {
  private final Provider<Context> contextProvider;

  public AivaLocationManager_Factory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public AivaLocationManager get() {
    return newInstance(contextProvider.get());
  }

  public static AivaLocationManager_Factory create(Provider<Context> contextProvider) {
    return new AivaLocationManager_Factory(contextProvider);
  }

  public static AivaLocationManager newInstance(Context context) {
    return new AivaLocationManager(context);
  }
}
