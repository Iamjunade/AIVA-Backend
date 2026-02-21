# Privacy Policy for AIVA (AI Vision Assistant)

**Last updated**: February 19, 2026

AIVA ("we", "our", or "us") is committed to protecting your privacy. This Privacy Policy explains how we collect, use, and safeguard your information when you use our mobile application.

## 1. Information Collection and Use

AIVA processes locally collected data to provide assistance to visually impaired users.

### 1.1 Camera Data
**Usage**: The app captures real-time video frames solely for the purpose of analyzing your surroundings (object detection, depth estimation, OCR).
**Data Handling**: Frames are transmitted securely (encrypted via WSS/TLS) to your personal AIVA server instance. Images are processed in memory and are **not** permanently stored unless you explicitly save a debug log. They are never shared with third parties.

### 1.2 Audio Data
**Usage**: The app records audio when you use voice commands (e.g., "Help", "Where am I").
**Data Handling**: Audio is transcribed on your personal server. No audio functionality is active when the app is in the background or not in use.

### 1.3 Location Data
**Usage**: The app accesses your location to answer "Where am I" queries and to generate Google Maps links for SOS messages.
**Data Handling**: Location is accessed only when you request it or trigger an SOS. Background location access is required to ensure SOS functionality works even if the phone is in your pocket. Location data is **not** tracked continuously or shared with advertisers.

## 2. Emergency SOS (SMS)
**Usage**: The app sends SMS messages to your pre-configured emergency contacts when you trigger the SOS feature.
**Data Handling**: The app creates and sends an SMS containing your current location directly from your device. We do not store or view your contacts.

## 3. Data Security
All communication between the Android client and your personal server is secured using SSL/TLS encryption. Authentication tokens (JWT) are stored securely on your device using Android EncryptedSharedPreferences.

## 4. Third-Party Services
The app uses Google Play Services for location and Firebase for crash reporting (Crashlytics) and performance monitoring. These services may collect anonymous usage data adhering to Google's Privacy Policy.

## 5. Contact Us
If you have questions about this Privacy Policy, please contact us at [your-email@example.com].
