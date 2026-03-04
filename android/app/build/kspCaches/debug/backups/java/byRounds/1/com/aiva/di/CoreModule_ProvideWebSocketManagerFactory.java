package com.aiva.di;

import com.aiva.core.connection.JwtTokenManager;
import com.aiva.core.connection.WebSocketManager;
import dagger.internal.DaggerGenerated;
import dagger.internal.Factory;
import dagger.internal.Preconditions;
import dagger.internal.QualifierMetadata;
import dagger.internal.ScopeMetadata;
import javax.annotation.processing.Generated;
import javax.inject.Provider;

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
  private final Provider<JwtTokenManager> jwtTokenManagerProvider;

  public CoreModule_ProvideWebSocketManagerFactory(
      Provider<JwtTokenManager> jwtTokenManagerProvider) {
    this.jwtTokenManagerProvider = jwtTokenManagerProvider;
  }

  @Override
  public WebSocketManager get() {
    return provideWebSocketManager(jwtTokenManagerProvider.get());
  }

  public static CoreModule_ProvideWebSocketManagerFactory create(
      Provider<JwtTokenManager> jwtTokenManagerProvider) {
    return new CoreModule_ProvideWebSocketManagerFactory(jwtTokenManagerProvider);
  }

  public static WebSocketManager provideWebSocketManager(JwtTokenManager jwtTokenManager) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideWebSocketManager(jwtTokenManager));
  }
}
