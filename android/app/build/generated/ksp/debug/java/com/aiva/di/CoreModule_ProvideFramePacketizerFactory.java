package com.aiva.di;

import com.aiva.core.protocol.FramePacketizer;
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
public final class CoreModule_ProvideFramePacketizerFactory implements Factory<FramePacketizer> {
  @Override
  public FramePacketizer get() {
    return provideFramePacketizer();
  }

  public static CoreModule_ProvideFramePacketizerFactory create() {
    return InstanceHolder.INSTANCE;
  }

  public static FramePacketizer provideFramePacketizer() {
    return Preconditions.checkNotNullFromProvides(CoreModule.INSTANCE.provideFramePacketizer());
  }

  private static final class InstanceHolder {
    private static final CoreModule_ProvideFramePacketizerFactory INSTANCE = new CoreModule_ProvideFramePacketizerFactory();
  }
}
