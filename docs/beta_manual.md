# AIVA Beta Testing Guide

This guide explains how to distribute and test the AIVA Android app using the Google Play Console Internal Testing track.

## 1. Prerequisites
- Access to the [Google Play Console](https://play.google.com/console).
- A valid Google account for each tester.
- A physical Android device (Emulator does not support Bluetooth/Sensors reliably).

## 2. Distributing a New Build
Our CI/CD pipeline automatically builds a release bundle (`.aab`) when you push a new tag (e.g., `v1.0.0`) to GitHub.

1. **Tag a Release**:
   ```bash
   git tag v1.0.1
   git push origin v1.0.1
   ```
2. **Download Artifact**:
   - Go to GitHub -> Actions -> Release Android -> Artifacts.
   - Download `app-release.aab`.
3. **Upload to Play Console**:
   - Navigate to **Testing > Internal testing**.
   - Click **Create new release**.
   - Upload the `.aab` file.
   - Add release notes (e.g., "Added SOS feature").
   - Click **Next** and **Save**.

## 3. Managing Testers
1. In Play Console, go to **Testing > Internal testing > Testers**.
2. Create an email list (e.g., "AIVA Alpha Team").
3. Add tester email addresses.
4. Copy the **Join on the web** link and share it with testers.

## 4. Testing Instructions (for Testers)
1. Open the invite link on your Android device.
2. Accept the invitation.
3. Click "Download it on Google Play".
4. Install the app.

## 5. Reporting Bugs
- **Crash**: If the app crashes, a report is automatically sent to Firebase Crashlytics.
- **Visual/Logic Bug**: Take a screenshot and share it in the #aiva-beta Slack channel.
- **Logs**: If possible, attach logs: `adb logcat -d > log.txt`.

## 6. Feedback Loop
- Performance metrics (startup time, frame rate) are tracked in **Firebase Performance**.
- Crash clusters are prioritized in **Firebase Crashlytics**.
