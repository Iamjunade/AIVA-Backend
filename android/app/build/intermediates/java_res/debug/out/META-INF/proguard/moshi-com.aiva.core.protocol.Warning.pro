-if class com.aiva.core.protocol.Warning
-keepnames class com.aiva.core.protocol.Warning
-if class com.aiva.core.protocol.Warning
-keep class com.aiva.core.protocol.WarningJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
