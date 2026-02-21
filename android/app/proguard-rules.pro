# Add project specific ProGuard rules here.
# By default, the flags in this file are appended to flags specified
# in /Users/junaidpasha/AppData/Local/Android/Sdk/tools/proguard/proguard-android.txt
# You can edit the include path and order by changing the proguardFiles
# directive in build.gradle.

# Hilt / Dagger
-keep class com.aiva.di.** { *; }
-keep class hilt_aggregated_deps.** { *; }
-keep class dagger.hilt.** { *; }

# Moshi
-keep class com.squareup.moshi.** { *; }
-keep interface com.squareup.moshi.** { *; }
-keepattributes Signature
-keepattributes *Annotation*
-dontwarn com.squareup.moshi.**

# Retrofit / OkHttp
-dontwarn retrofit2.**
-keep class retrofit2.** { *; }
-keepattributes Exceptions
-dontwarn okhttp3.**
-dontwarn okio.**

# CameraX
-keep class androidx.camera.** { *; }

# Coroutines
-keep class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**

# Android Components (if not covered by default)
-keep public class * extends android.app.Activity
-keep public class * extends android.app.Application
-keep public class * extends android.app.Service
-keep public class * extends android.content.BroadcastReceiver
-keep public class * extends android.content.ContentProvider

# Data Classes (Moshi)
-keep class com.aiva.core.protocol.** { *; }
-keep class com.aiva.data.model.** { *; }
