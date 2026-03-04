package com.aiva.di;

import android.content.Context;
import com.aiva.core.connection.JwtTokenManager;
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
public final class CoreModule_ProvideJwtTokenManagerFactory implements Factory<JwtTokenManager> {
  private final Provider<Context> contextProvider;

  public CoreModule_ProvideJwtTokenManagerFactory(Provider<Context> contextProvider) {
    this.contextProvider = contextProvider;
  }

  @Override
  public JwtTokenManager get() {
    return provideJwtTokenManager(contextProvider.get());
  }

  public static CoreModule_ProvideJwtTokenManagerFactory create(Provider<Context> contextProvider) {
    return new CoreModule_ProvideJwtTokenManagerFactory(contextProvider);
  }

  public static JwtTokenManager provideJwtTokenManager(Context context) {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideJwtTokenManager(context));
  }
}
