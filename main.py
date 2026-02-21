"""
AIVA - AI Vision Assistant
===========================
Real-time AI-powered assistant for visually impaired individuals.

Combines computer vision (object detection, depth estimation),
spatial intelligence (obstacle avoidance), and voice interaction
(speech recognition + TTS) into a unified assistive system.

Phase 1: Vision + Voice Foundation
Phase 2: Spatial Intelligence + Navigation Logic

Modules:
    - ObjectDetector: YOLOv8 Nano (80 COCO classes, >0.6 confidence)
    - DepthEstimator: MiDaS Small (monocular depth → approx meters)
    - SpatialEngine: Obstacle avoidance + environment awareness
    - SpeechEngine: Whisper STT + intent classification + TTS
    - AssistantAI: Gemini cloud AI for scene description + OCR
    - FaceDetector: Local face recognition (retained from VASIS)
    - VideoGet: Threaded video capture

Usage:
    python main.py

Controls (Keyboard — dev/testing):
    v - Voice command (listen for speech)
    w - What's around me? (environment awareness)
    d - Describe scene (AI)
    r - Read text (AI/OCR)
    q - Quit

Voice Commands:
    "What's around me?" → List nearest objects
    "Describe" / "What do you see?" → AI scene description
    "Read text" → OCR
    "Emergency" → Emergency trigger (Phase 3)
"""

import sys
import time
import threading
from pathlib import Path

import cv2
import numpy as np

# Core modules
from src.video_stream import VideoGet
from src.face_detector import FaceDetector, draw_face_boxes
from src.assistant_ai import AssistantAI

# New AIVA modules
from src.object_detector import ObjectDetector, Detection
from src.depth_estimator import DepthEstimator
from src.spatial_engine import SpatialEngine, Warning
from src.speech_engine import SpeechEngine, Intent, classify_intent, TextToSpeech


# =============================================================================
# CONFIGURATION
# =============================================================================

# Video source: 0 = laptop webcam, or IP Webcam URL
VIDEO_SOURCE = 0

# Face recognition
KNOWN_FACES_DIR = "known_faces"
FACE_DETECTION_FRAME_SKIP = 10

# Object detection
OBJECT_DETECTION_ENABLED = True
DEPTH_ESTIMATION_ENABLED = True

# Depth estimation runs less frequently than object detection for performance
DEPTH_FRAME_SKIP = 3  # Run depth every Nth detection frame

# Obstacle warning settings
OBSTACLE_WARNINGS_ENABLED = True
WARNING_SPEAK_COOLDOWN = 3.0  # Seconds between spoken warnings

# Voice command settings
VOICE_ENABLED = True

# Display settings
WINDOW_NAME = "AIVA - AI Vision Assistant"
WINDOW_WIDTH = 960
WINDOW_HEIGHT = 540
SHOW_DEPTH_MAP = False  # Toggle depth visualization (press 'm')


# =============================================================================
# MAIN APPLICATION
# =============================================================================

def main():
    """Main AIVA application loop."""
    print("=" * 60)
    print("  AIVA - AI Vision Assistant")
    print("  Phase 1 & 2: Vision + Voice + Spatial Intelligence")
    print("  Founder: Junaid Pasha")
    print("=" * 60)

    # ---- Step 1: Initialize TTS first (for startup announcements) ----
    print("\n[1/7] Initializing speech engine...")
    speech = SpeechEngine()
    tts = speech.tts

    # ---- Step 2: Initialize AI Assistant ----
    print("\n[2/7] Initializing AI assistant...")
    assistant = AssistantAI()
    ai_status = "Ready" if assistant.is_available else "Unavailable"
    print(f"  AI assistant: {ai_status}")

    # ---- Step 3: Initialize Object Detector ----
    print("\n[3/7] Initializing object detector...")
    detector = None
    if OBJECT_DETECTION_ENABLED:
        detector = ObjectDetector()
        if detector.is_available:
            print("  ✓ Object detection ready")
        else:
            print("  ✗ Object detection unavailable")
            detector = None

    # ---- Step 4: Initialize Depth Estimator ----
    print("\n[4/7] Initializing depth estimator...")
    depth_estimator = None
    if DEPTH_ESTIMATION_ENABLED:
        depth_estimator = DepthEstimator()
        if depth_estimator.is_available:
            print("  ✓ Depth estimation ready")
        else:
            print("  ✗ Depth estimation unavailable")
            depth_estimator = None

    # ---- Step 5: Initialize Spatial Engine ----
    print("\n[5/7] Initializing spatial engine...")
    spatial = SpatialEngine()
    print("  ✓ Spatial engine ready")

    # ---- Step 6: Initialize Face Detector ----
    print("\n[6/7] Loading face database...")
    face_detector = FaceDetector(
        known_faces_dir=KNOWN_FACES_DIR,
        frame_skip=FACE_DETECTION_FRAME_SKIP
    )
    face_count = face_detector.load_known_faces()
    if face_count == 0:
        print(f"  TIP: Add photos to '{KNOWN_FACES_DIR}/' for face recognition")

    # ---- Step 7: Initialize Video Stream ----
    print(f"\n[7/7] Connecting to video source: {VIDEO_SOURCE}")
    video = VideoGet(src=VIDEO_SOURCE).start()

    # Wait for first frame
    print("Waiting for video stream...")
    start_time = time.time()
    timeout = 10.0

    while video.read() is None:
        if time.time() - start_time > timeout:
            print("\n[ERROR] Timeout waiting for video stream!")
            print("Check your camera connection.")
            video.stop()
            return 1
        time.sleep(0.1)

    # ---- System Ready ----
    print("\n" + "=" * 60)
    print("✓ AIVA System Ready!")
    print(f"  • Object Detection: {'ON' if detector else 'OFF'}")
    print(f"  • Depth Estimation: {'ON' if depth_estimator else 'OFF'}")
    print(f"  • Spatial Warnings: {'ON' if OBSTACLE_WARNINGS_ENABLED else 'OFF'}")
    print(f"  • Voice Commands:   {'ON' if speech.is_available else 'OFF (keyboard only)'}")
    print(f"  • AI Assistant:     {ai_status}")
    print(f"  • Known Faces:      {face_count}")
    print()
    print("  Keyboard Controls:")
    print("    'v' - Voice command (speak to AIVA)")
    print("    'w' - What's around me?")
    print("    'd' - Describe scene (AI)")
    print("    'r' - Read text (AI/OCR)")
    print("    'm' - Toggle depth map view")
    print("    'q' - Quit")
    print("=" * 60)

    # Announce system ready
    tts.speak("AIVA system ready. You can speak commands or use keyboard shortcuts.")

    # ---- Create Display Window ----
    cv2.namedWindow(WINDOW_NAME, cv2.WINDOW_NORMAL)
    cv2.resizeWindow(WINDOW_NAME, WINDOW_WIDTH, WINDOW_HEIGHT)

    # ---- State Variables ----
    display_fps = 0.0
    frame_count = 0
    fps_start_time = time.time()
    detection_frame_count = 0

    # Face announcement tracking
    previously_visible_names = set()
    last_face_announcement_time = {}
    FACE_ANNOUNCEMENT_COOLDOWN = 10.0

    # Obstacle warning tracking
    last_warning_speak_time = 0.0

    # Current detections (shared between loops)
    current_detections: list = []
    current_depth_map = None
    show_depth = SHOW_DEPTH_MAP

    # Voice command processing flag
    voice_processing = False

    try:
        while True:
            frame = video.read()

            if frame is None:
                placeholder = _create_placeholder(
                    "Reconnecting...", WINDOW_WIDTH, WINDOW_HEIGHT
                )
                cv2.imshow(WINDOW_NAME, placeholder)
                cv2.waitKey(1)
                continue

            # ---- FPS Calculation ----
            frame_count += 1
            elapsed = time.time() - fps_start_time
            if elapsed >= 1.0:
                display_fps = frame_count / elapsed
                frame_count = 0
                fps_start_time = time.time()

            frame_height, frame_width = frame.shape[:2]

            # ---- Object Detection ----
            if detector and detector.is_available:
                current_detections = detector.detect(frame)

                # ---- Depth Estimation (every Nth frame) ----
                detection_frame_count += 1
                if depth_estimator and detection_frame_count % DEPTH_FRAME_SKIP == 0:
                    current_depth_map = depth_estimator.estimate(frame)

                    # Enrich detections with distance and direction
                    if current_depth_map is not None:
                        depth_estimator.enrich_detections(
                            current_detections, current_depth_map, frame_width
                        )

                # ---- Obstacle Warnings ----
                if OBSTACLE_WARNINGS_ENABLED and current_detections:
                    current_time = time.time()

                    # Quick danger check
                    danger = spatial.get_danger_summary(current_detections)
                    if danger and current_time - last_warning_speak_time > WARNING_SPEAK_COOLDOWN:
                        print(f"\n🚨 {danger}")
                        tts.speak(danger)
                        last_warning_speak_time = current_time

                    # Standard obstacle check
                    elif current_time - last_warning_speak_time > WARNING_SPEAK_COOLDOWN:
                        warnings = spatial.check_obstacles(current_detections)
                        if warnings:
                            # Speak the most urgent warning
                            top_warning = warnings[0]
                            if top_warning.is_critical:
                                print(f"\n⚠️ {top_warning.message}")
                                tts.speak(top_warning.message)
                                last_warning_speak_time = current_time

                # Draw object detections
                detector.draw_detections(frame, current_detections)

            # ---- Face Detection ----
            faces = face_detector.detect_and_identify(frame)

            # Auto-announce newly visible known faces
            current_names = set()
            for name, _ in faces:
                if name != "Unknown":
                    current_names.add(name)

            new_faces = current_names - previously_visible_names
            current_time = time.time()

            for name in new_faces:
                last_time = last_face_announcement_time.get(name, 0)
                if current_time - last_time > FACE_ANNOUNCEMENT_COOLDOWN:
                    announcement = f"{name} is here"
                    print(f"\n🎤 [FACE] {announcement}")
                    tts.speak(announcement)
                    last_face_announcement_time[name] = current_time

            previously_visible_names = current_names
            draw_face_boxes(frame, faces)

            # ---- Draw Status Overlay ----
            _draw_status_overlay(
                frame,
                capture_fps=video.fps,
                display_fps=display_fps,
                connected=video.is_connected,
                current_person=face_detector.current_person_visible,
                known_count=face_detector.known_face_count,
                detection_count=len(current_detections),
                voice_active=voice_processing
            )

            # ---- Display ----
            if show_depth and current_depth_map is not None and depth_estimator:
                # Side-by-side: camera + depth map
                depth_color = depth_estimator.get_depth_colormap(current_depth_map)
                depth_color = cv2.resize(depth_color, (frame_width, frame_height))
                combined = np.hstack([frame, depth_color])
                cv2.imshow(WINDOW_NAME, combined)
            else:
                cv2.imshow(WINDOW_NAME, frame)

            # ---- Keyboard Input ----
            key = cv2.waitKey(1) & 0xFF

            if key == ord('q'):
                print("\nQuitting...")
                break

            elif key == ord('v') and not voice_processing:
                # Voice command
                voice_processing = True
                print("\n🎙️ Listening for voice command...")
                tts.speak("Listening.")

                def _handle_voice():
                    nonlocal voice_processing
                    try:
                        text, intent = speech.listen_and_classify(duration=5.0)
                        _handle_intent(
                            intent, text, frame, assistant,
                            current_detections, spatial, tts
                        )
                    finally:
                        voice_processing = False

                threading.Thread(target=_handle_voice, daemon=True).start()

            elif key == ord('w'):
                # What's around me?
                summary = spatial.get_surroundings(current_detections)
                print(f"\n🌍 {summary}")
                tts.speak(summary)

            elif key == ord('d') and frame is not None:
                # Describe scene (AI)
                print("\n[AI] Analyzing scene...")
                response = assistant.describe_scene(frame)
                print(f"\n🔊 SCENE: {response}")
                tts.speak(response)

            elif key == ord('r') and frame is not None:
                # Read text (AI/OCR)
                print("\n[AI] Reading text...")
                response = assistant.read_text(frame)
                print(f"\n📖 TEXT: {response}")
                tts.speak(response)

            elif key == ord('m'):
                # Toggle depth map
                show_depth = not show_depth
                print(f"\n{'Showing' if show_depth else 'Hiding'} depth map")

    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n[ERROR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    finally:
        video.stop()
        cv2.destroyAllWindows()
        print("AIVA shutdown complete. Goodbye!")

    return 0


def _handle_intent(
    intent: Intent,
    text: str,
    frame,
    assistant: AssistantAI,
    detections: list,
    spatial: SpatialEngine,
    tts: TextToSpeech
):
    """
    Handle a classified voice command intent.

    Args:
        intent: Classified intent from speech
        text: Original transcribed text
        frame: Current video frame
        assistant: AI assistant for cloud queries
        detections: Current object detections
        spatial: Spatial engine
        tts: Text-to-speech engine
    """
    print(f"\n[INTENT] {intent.value} — \"{text}\"")

    if intent == Intent.SURROUNDINGS:
        summary = spatial.get_surroundings(detections)
        print(f"  🌍 {summary}")
        tts.speak(summary)

    elif intent == Intent.DESCRIBE:
        if frame is not None and assistant.is_available:
            print("  [AI] Analyzing scene...")
            response = assistant.describe_scene(frame)
            print(f"  🔊 {response}")
            tts.speak(response)
        else:
            tts.speak("Scene description is not available right now.")

    elif intent == Intent.READ_TEXT:
        if frame is not None and assistant.is_available:
            print("  [AI] Reading text...")
            response = assistant.read_text(frame)
            print(f"  📖 {response}")
            tts.speak(response)
        else:
            tts.speak("Text reading is not available right now.")

    elif intent == Intent.EMERGENCY:
        print("  🚨 EMERGENCY TRIGGERED")
        tts.speak("Emergency mode activated. This feature will be available in a future update.")
        # Phase 3: GPS location + contact call + SMS

    elif intent == Intent.LOCATION:
        tts.speak("Location services will be available in a future update.")

    elif intent == Intent.BATTERY:
        # Could integrate with system APIs
        tts.speak("Battery status will be available in a future update.")

    elif intent == Intent.INTERNET:
        tts.speak("Internet status will be available in a future update.")

    elif intent == Intent.UNKNOWN:
        tts.speak("I did not understand. Please repeat.")


def _draw_status_overlay(
    frame,
    capture_fps: float,
    display_fps: float,
    connected: bool,
    current_person: str,
    known_count: int,
    detection_count: int = 0,
    voice_active: bool = False
):
    """Draw AIVA status information on the frame."""
    overlay_height = 110
    overlay = frame[:overlay_height, :].copy()
    cv2.rectangle(frame, (0, 0), (frame.shape[1], overlay_height), (0, 0, 0), -1)
    cv2.addWeighted(overlay, 0.3, frame[:overlay_height, :], 0.7, 0, frame[:overlay_height, :])

    # Title
    cv2.putText(frame, "AIVA - AI Vision Assistant", (10, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # Connection status
    status_color = (0, 255, 0) if connected else (0, 0, 255)
    status_text = "CONNECTED" if connected else "DISCONNECTED"
    cv2.putText(frame, f"Stream: {status_text}", (10, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, status_color, 1)

    # Current person visible
    person_color = (0, 255, 0) if current_person not in ["No one", "Unknown person"] else (0, 165, 255)
    cv2.putText(frame, f"Visible: {current_person}", (10, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, person_color, 2)

    # Object detection count
    cv2.putText(frame, f"Objects: {detection_count} | Faces DB: {known_count}", (10, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.4, (200, 200, 200), 1)

    # Voice indicator
    if voice_active:
        cv2.putText(frame, "MIC ACTIVE", (10, 107),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 255), 1)

    # Right side — FPS and controls
    fps_x = frame.shape[1] - 200
    cv2.putText(frame, f"Capture: {capture_fps:.1f} FPS", (fps_x, 25),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv2.putText(frame, f"Display: {display_fps:.1f} FPS", (fps_x, 48),
                cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 255, 255), 1)
    cv2.putText(frame, "v:voice w:around d:desc", (fps_x, 70),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)
    cv2.putText(frame, "r:read m:depth q:quit", (fps_x, 90),
                cv2.FONT_HERSHEY_SIMPLEX, 0.35, (150, 150, 150), 1)


def _create_placeholder(message: str, width: int, height: int):
    """Create a placeholder frame with a message."""
    frame = np.zeros((height, width, 3), dtype=np.uint8)
    frame[:] = (40, 40, 40)

    font = cv2.FONT_HERSHEY_SIMPLEX
    text_size = cv2.getTextSize(message, font, 1.0, 2)[0]
    x = (width - text_size[0]) // 2
    y = (height + text_size[1]) // 2
    cv2.putText(frame, message, (x, y), font, 1.0, (0, 165, 255), 2)

    return frame


if __name__ == "__main__":
    sys.exit(main())
