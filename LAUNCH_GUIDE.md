# AIVA Launch & Demo Guide

Follow these steps to launch the complete AIVA system for your hackathon presentation.

## 1. Prerequisites
- **Computer**: Windows/Linux/Mac with Python 3.10+ installed.
- **Android Phone**: Developer Mode enabled, connected via USB.
- **Wi-Fi**: Both devices should ideally be on the same network (or use USB tethering).

## 2. Start the Python Backend (The "Brain")
1. Open a terminal in the `VASIS` directory.
2. Activate your virtual environment (if used):
   ```powershell
   # Windows
   .\venv\Scripts\activate
   ```
3. Run the server:
   ```powershell
   python -m server.aiva_server
   ```
   *You should see: `Server listening on 0.0.0.0:8765`*

## 3. Connect Android Client (The "Sensor")

### Option A: USB Cable (Recommended for lowest latency)
1. Ensure your phone is connected.
2. Run the ADB reverse command to forward the WebSocket port:
   ```powershell
   adb reverse tcp:8765 tcp:8765
   ```
3. Build and install the app (if not already installed):
   ```powershell
   cd android
   .\gradlew installDebug
   ```
4. Open the **AIVA** app on your phone.
5. Go to **Settings** -> **Server URL**.
6. Enter: `ws://localhost:8765` (Yes, "localhost" works because of `adb reverse`).

### Option B: Wi-Fi (No cable)
1. Find your computer's local IP address (e.g., `192.168.1.5`).
2. Open the **AIVA** app.
3. Go to **Settings** -> **Server URL**.
4. Enter: `ws://192.168.1.5:8765`

## 4. Running the Demo
1. **Connect**: Tap the **Start** button on the concept home screen.
   - Status should change to **Connected**.
   - Review the server terminal—you should see "Client connected".

2. **Test Vision**:
   - Point the camera at objects (Chair, Person, Bottle).
   - *Listen*: The app should speak "Chair ahead", "Person nearby".

3. **Test Voice Commands**:
   - Tap the screen (or use volume button trigger if configured).
   - Say: **"What is in front of me?"** -> *AI describes the scene.*
   - Say: **"Read this text"** -> *AI reads visible text.*
   - Say: **"Where am I?"** -> *AI gives current address.*
   - Say: **"Help me"** -> *AI triggers SOS (sends SMS).*

## 5. Troubleshooting
- **Connection Failed/Cycling**:
  - Check if `adb reverse` was run.
  - Check Windows Firewall (Allow Python to accept connections).
  - Ensure both devices are on the same Wi-Fi.
- **No Audio**: Check phone media volume.
- **Camera Black**: Check App Permissions (Camera, Location).

## 6. Deployment FAQ
### Can I deploy this to Vercel / Netlify?
**No.** Vercel is designed for **stateless** web apps and serverless functions (short-lived).
AIVA requires:
1.  **Long-lived WebSockets**: For real-time video streaming. Serverless functions kill connections after ~30s.
2.  **Persistent Memory (RAM)**: YOLO/MiDaS models take 3-5 seconds to load. Serverless would reload them for *every frame*, causing massive lag.
3.  **GPU Acceleration**: Real-time object detection needs a GPU (or fast CPU), which Vercel does not provide.

**Best for Hackathon:** Run locally on your laptop (Localhost).
**Best for Production:** Docker container on AWS EC2 (g4dn.xlarge) or Google Cloud Run (with GPU).

Good luck with the demo!
