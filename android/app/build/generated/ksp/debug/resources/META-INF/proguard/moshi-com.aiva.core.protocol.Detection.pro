-if class com.aiva.core.protocol.Detection
-keepnames class com.aiva.core.protocol.Detection
-if class com.aiva.core.protocol.Detection
-keep class com.aiva.core.protocol.DetectionJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
