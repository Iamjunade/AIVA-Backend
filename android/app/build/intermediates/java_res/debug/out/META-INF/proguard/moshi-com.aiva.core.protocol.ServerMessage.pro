-if class com.aiva.core.protocol.ServerMessage
-keepnames class com.aiva.core.protocol.ServerMessage
-if class com.aiva.core.protocol.ServerMessage
-keep class com.aiva.core.protocol.ServerMessageJsonAdapter {
    public <init>(com.squareup.moshi.Moshi);
}
-if class com.aiva.core.protocol.ServerMessage
-keepnames class kotlin.jvm.internal.DefaultConstructorMarker
-if class com.aiva.core.protocol.ServerMessage
-keepclassmembers class com.aiva.core.protocol.ServerMessage {
    public synthetic <init>(java.lang.String,java.lang.Integer,java.lang.Long,java.lang.Integer,java.util.List,java.util.List,java.lang.String,java.lang.Boolean,java.lang.String,java.lang.String,int,kotlin.jvm.internal.DefaultConstructorMarker);
}
