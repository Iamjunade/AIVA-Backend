package com.aiva.di;

import com.aiva.core.connection.WebSocketManager;
import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
import dagger.internal.Preconditions;
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
public final class CoreModule_ProvideWebSocketManagerFactory implements Factory<WebSocketManager> {
  @Override
  public WebSocketManager get() {
    return provideWebSocketManager();
  }

  public static CoreModule_ProvideWebSocketManagerFactory create() {
    return InstanceHolder.INSTANCE;
  }

  public static WebSocketManager provideWebSocketManager() {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideWebSocketManager());
  }

  private static final class InstanceHolder {
    private static final CoreModule_ProvideWebSocketManagerFactory INSTANCE = new CoreModule_ProvideWebSocketManagerFactory();
  }
}
