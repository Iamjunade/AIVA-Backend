@echo off
echo =======================================================
echo              AIVA Master Startup System
echo =======================================================
echo.

:: 1. Navigate to the script directory
cd /d "%~dp0"

:: 2. Activate Python virtual environment if it exists
if exist "venv\Scripts\activate.bat" (
    echo [INFO] Activating virtual environment...
    call "venv\Scripts\activate.bat"
) else (
    echo [INFO] No virtual environment found. Using system Python.
)

:: 3. Set performance variables for CPU inference
echo [INFO] Configuring YOLO and Performance Settings...
set AIVA_YOLO_IMG_SIZE=320

:: 4. Start ADB Reverse Tunnel for Android app WebSocket connection
echo [INFO] Establishing ADB reverse port tunnel (8765)...
echo Make sure your Android device is connected via USB!
"%LOCALAPPDATA%\Android\Sdk\platform-tools\adb.exe" reverse tcp:8765 tcp:8765
if %ERRORLEVEL% neq 0 (
    echo [WARNING] ADB reverse failed. If you are using Wi-Fi, you can ignore this.
) else (
    echo [SUCCESS] ADB reverse tunnel established.
)
echo.

:: 5. Launch the AIVA Server
echo [INFO] Starting AIVA Backend Server...
python -m server.aiva_server

pause
