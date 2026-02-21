package com.aiva.di;

import android.content.Context;
import com.aiva.core.camera.CameraManager;
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
public final class CoreModule_ProvideCameraManagerFactory implements Factory<CameraManager> {
  private final Provider<Context> contextProvider;

  public CoreModule_ProvideCameraManagerFactory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public CameraManager get() {
    return provideCameraManager(contextProvider.get());
  }

  public static CoreModule_ProvideCameraManagerFactory create(Provider<Context> contextProvider) {
    return new CoreModule_ProvideCameraManagerFactory(contextProvider);
  }

  public static CameraManager provideCameraManager(Context context) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideCameraManager(context));
  }
}
