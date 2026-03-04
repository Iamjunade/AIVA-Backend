@echo off
cd c:\Users\junaidpasha\Downloads\VASIS\android
call "C:\Program Files\Microsoft\jdk-17.0.17.10-hotspot\bin\java.exe" -classpath gradle\wrapper\gradle-wrapper.jar org.gradle.wrapper.GradleWrapperMain assembleDebug
if %ERRORLEVEL% NEQ 0 (
    echo Gradle build failed.
    exit /b %ERRORLEVEL%
)

echo Installing APK...
call "C:\Users\junaidpasha\AppData\Local\Android\Sdk\platform-tools\adb.exe" install -r app\build\outputs\apk\debug\app-debug.apk
call "C:\Users\junaidpasha\AppData\Local\Android\Sdk\platform-tools\adb.exe" shell am start -n com.aiva/.MainActivity

echo Starting Server...
cd c:\Users\junaidpasha\Downloads\VASIS
python -m server.aiva_server
