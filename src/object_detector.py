"""
AIVA - Object Detection Engine
===============================
Real-time object detection using YOLOv8 Nano for lightweight on-device inference.

Detects 80 COCO classes at ≥20 FPS with confidence threshold enforcement (>0.6)
to prevent false positives (anti-hallucination constraint from PRD).

Technology: Ultralytics YOLOv8n (~6MB model, auto-downloaded)
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

import numpy as np

try:
    from ultralytics import YOLO
    YOLO_AVAILABLE = True
except ImportError:
    YOLO_AVAILABLE = False
    print("[ObjectDetector] WARNING: ultralytics not installed. Run: pip install ultralytics")


@dataclass
class Detection:
    """A single detected object with spatial metadata."""
    class_name: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (x1, y1, x2, y2) in pixels
    center_x: int  # Center X in pixels
    center_y: int  # Center Y in pixels
    # Populated by depth estimator later
    distance_m: Optional[float] = None
    direction: Optional[str] = None  # "left", "center", "right"

    @property
    def area(self) -> int:
        """Bounding box area in pixels."""
        x1, y1, x2, y2 = self.bbox
        return (x2 - x1) * (y2 - y1)


# Priority classes for safety warnings (higher index = lower priority)
SAFETY_PRIORITY_CLASSES = {
    # Moving vehicles — highest priority
    "car": 0, "truck": 0, "bus": 0, "motorcycle": 0,
    # Stairs/steps — very high priority (approximated by COCO classes)
    "bicycle": 1,
    # Animals
    "dog": 2, "cat": 2, "horse": 2,
    # Persons
    "person": 3,
    # Static obstacles
    "bench": 4, "fire hydrant": 4, "stop sign": 4,
    "parking meter": 4, "chair": 4, "couch": 4,
    "dining table": 4, "potted plant": 4, "suitcase": 4,
}

# Safety-critical classes that bypass temporal confirmation
_SAFETY_BYPASS_CLASSES = {"car", "truck", "bus", "motorcycle", "bicycle"}


@dataclass
class _TrackEntry:
    """Internal tracking state for a detection across frames."""
    detection: Detection
    seen_count: int = 1       # Consecutive frames seen
    missed_count: int = 0     # Consecutive frames missed
    confirmed: bool = False   # Whether this detection is confirmed


class DetectionTracker:
    """
    Temporal detection smoother — eliminates single-frame phantom detections.

    An object must appear in N consecutive frames before being reported.
    Safety-critical objects (vehicles) bypass confirmation and are reported
    immediately. Disappeared objects persist briefly to prevent flicker.

    This is the primary defense against YOLO false positives that cause
    phantom 'car ahead' or 'traffic light' announcements.
    """

    def __init__(self, confirm_frames: int = 2, expire_frames: int = 3):
        """
        Args:
            confirm_frames: Frames to confirm a NEW object (default: 2)
            expire_frames: Frames before a GONE object is removed (default: 3)
        """
        self._confirm_frames = confirm_frames
        self._expire_frames = expire_frames
        self._tracks: Dict[str, _TrackEntry] = {}

    def smooth(self, raw_detections: List[Detection]) -> List[Detection]:
        """
        Filter detections through temporal smoothing.

        Args:
            raw_detections: Current frame's raw YOLO detections

        Returns:
            Smoothed detections — only confirmed objects
        """
        # Build a lookup of current detections by class+direction key
        current_keys: Dict[str, Detection] = {}
        for det in raw_detections:
            key = f"{det.class_name}@{det.direction or 'center'}"
            # Keep higher confidence if same key
            if key not in current_keys or det.confidence > current_keys[key].confidence:
                current_keys[key] = det

        # Update existing tracks
        updated_keys = set()
        for key, track in list(self._tracks.items()):
            if key in current_keys:
                # Object still present — update
                track.detection = current_keys[key]
                track.seen_count += 1
                track.missed_count = 0
                if track.seen_count >= self._confirm_frames:
                    track.confirmed = True
                updated_keys.add(key)
            else:
                # Object missing this frame
                track.missed_count += 1
                if track.missed_count >= self._expire_frames:
                    del self._tracks[key]

        # Add new tracks for unseen objects
        for key, det in current_keys.items():
            if key not in updated_keys and key not in self._tracks:
                is_safety = det.class_name in _SAFETY_BYPASS_CLASSES
                confirmed = is_safety or (1 >= self._confirm_frames)
                self._tracks[key] = _TrackEntry(
                    detection=det,
                    seen_count=1,
                    missed_count=0,
                    confirmed=confirmed,
                )

        # Return only confirmed detections
        return [
            track.detection
            for track in self._tracks.values()
            if track.confirmed
        ]

    def reset(self):
        """Clear all tracking state."""
        self._tracks.clear()

class ObjectDetector:
    """
    YOLOv8 Nano object detector optimized for assistive vision.

    Provides real-time object detection with strict confidence filtering
    to prevent false positives. All detections must exceed the configured
    confidence threshold (default 0.6 per PRD requirements).

    Usage:
        detector = ObjectDetector()
        detections = detector.detect(frame)
        for det in detections:
            print(f"{det.class_name} ({det.confidence:.0%}) at {det.direction}")
    """

    # Default model
    MODEL_NAME = "yolov8n.pt"

    # Minimum confidence — PRD mandates >0.6
    DEFAULT_CONFIDENCE = 0.6

    # Input image size for inference (smaller = faster)
    DEFAULT_IMG_SIZE = 640

    def __init__(
        self,
        model_name: str = MODEL_NAME,
        confidence_threshold: float = DEFAULT_CONFIDENCE,
        img_size: int = DEFAULT_IMG_SIZE,
        device: Optional[str] = None
    ):
        """
        Initialize the object detector.

        Args:
            model_name: YOLO model file (auto-downloaded if not present)
            confidence_threshold: Minimum confidence for detections (>0.6 per PRD)
            img_size: Input image size for inference
            device: Force device ('cuda', 'cpu', or None for auto)
        """
        self._model = None
        self._confidence_threshold = max(confidence_threshold, 0.6)  # Enforce PRD minimum
        self._img_size = img_size
        self._device = device
        self._class_names = {}
        self._frame_count = 0
        self._last_detections: List[Detection] = []

        if not YOLO_AVAILABLE:
            print("[ObjectDetector] Detection disabled — ultralytics not installed")
            return

        from server.config import YOLO_CLASS_OVERRIDES, DETECTION_CONFIRM_FRAMES, DETECTION_EXPIRE_FRAMES
        self._class_overrides = YOLO_CLASS_OVERRIDES

        # Temporal detection tracker (anti-flicker)
        self._tracker = DetectionTracker(
            confirm_frames=DETECTION_CONFIRM_FRAMES,
            expire_frames=DETECTION_EXPIRE_FRAMES,
        )

        self._load_model(model_name)

    def _load_model(self, model_name: str) -> None:
        """Load the YOLOv8 model."""
        try:
            print(f"[ObjectDetector] Loading model: {model_name}")
            self._model = YOLO(model_name)

            # Force a warmup inference to download model and compile
            import torch
            if self._device:
                device = self._device
            elif torch.cuda.is_available():
                device = "cuda"
                print("[ObjectDetector] ✓ CUDA GPU detected — using GPU acceleration")
            else:
                device = "cpu"
                print("[ObjectDetector] Using CPU inference")

            self._device = device

            # Get class names from model
            self._class_names = self._model.names
            print(f"[ObjectDetector] ✓ Model loaded ({len(self._class_names)} classes)")
            print(f"[ObjectDetector]   Confidence threshold: {self._confidence_threshold:.0%}")
            print(f"[ObjectDetector]   Image size: {self._img_size}px")
            print(f"[ObjectDetector]   Device: {self._device}")

        except Exception as e:
            print(f"[ObjectDetector] ✗ Failed to load model: {e}")
            self._model = None

    def detect(self, frame: np.ndarray) -> List[Detection]:
        """
        Run object detection on a frame.

        Args:
            frame: BGR image from OpenCV (numpy array)

        Returns:
            List of Detection objects, filtered by confidence threshold.
            Only returns detections with confidence > 0.6 (anti-hallucination).
        """
        if self._model is None:
            return []

        if frame is None or frame.size == 0:
            return self._last_detections

        try:
            self._frame_count += 1
            frame_height, frame_width = frame.shape[:2]

            # Run inference (verbose=False to suppress output)
            results = self._model.predict(
                source=frame,
                conf=self._confidence_threshold,
                imgsz=self._img_size,
                device=self._device,
                verbose=False,
                stream=False
            )

            detections: List[Detection] = []

            if results and len(results) > 0:
                result = results[0]

                if result.boxes is not None and len(result.boxes) > 0:
                    boxes = result.boxes

                    for i in range(len(boxes)):
                        # Extract bounding box
                        x1, y1, x2, y2 = boxes.xyxy[i].cpu().numpy().astype(int)

                        # Extract confidence and class
                        conf = float(boxes.conf[i].cpu().numpy())
                        cls_id = int(boxes.cls[i].cpu().numpy())
                        class_name = self._class_names.get(cls_id, f"class_{cls_id}")

                        # Enforce dynamic confidence threshold
                        threshold = self._class_overrides.get(class_name, self._confidence_threshold)
                        if conf < threshold:
                            continue

                        # Calculate center point
                        center_x = (x1 + x2) // 2
                        center_y = (y1 + y2) // 2

                        # Determine horizontal direction
                        relative_x = center_x / frame_width
                        if relative_x < 0.33:
                            direction = "left"
                        elif relative_x > 0.66:
                            direction = "right"
                        else:
                            direction = "center"

                        detection = Detection(
                            class_name=class_name,
                            confidence=conf,
                            bbox=(int(x1), int(y1), int(x2), int(y2)),
                            center_x=int(center_x),
                            center_y=int(center_y),
                            direction=direction
                        )
                        detections.append(detection)

            self._last_detections = detections

            # Temporal smoothing: confirm across frames
            if hasattr(self, '_tracker'):
                detections = self._tracker.smooth(detections)

            return detections

        except Exception as e:
            if self._frame_count <= 1:
                print(f"[ObjectDetector] Detection error: {e}")
            return self._last_detections

    def draw_detections(
        self,
        frame: np.ndarray,
        detections: List[Detection],
        color: Tuple[int, int, int] = (0, 255, 0),
        show_distance: bool = True
    ) -> None:
        """
        Draw detection bounding boxes and labels on frame (in-place).

        Args:
            frame: BGR image to draw on
            detections: List of Detection objects
            color: BGR color for boxes
            show_distance: Whether to show distance if available
        """
        import cv2

        for det in detections:
            x1, y1, x2, y2 = det.bbox

            # Color based on safety priority
            priority = SAFETY_PRIORITY_CLASSES.get(det.class_name, 5)
            if priority == 0:
                box_color = (0, 0, 255)  # Red — vehicles
            elif priority <= 2:
                box_color = (0, 165, 255)  # Orange — animals/bikes
            else:
                box_color = color  # Green — default

            # If close, override to red
            if det.distance_m is not None and det.distance_m < 1.5:
                box_color = (0, 0, 255)

            # Draw bounding box
            cv2.rectangle(frame, (x1, y1), (x2, y2), box_color, 2)

            # Build label
            label = f"{det.class_name} {det.confidence:.0%}"
            if show_distance and det.distance_m is not None:
                label += f" {det.distance_m:.1f}m"

            # Draw label background
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.5
            thickness = 1
            (tw, th), baseline = cv2.getTextSize(label, font, font_scale, thickness)
            cv2.rectangle(frame, (x1, y1 - th - 6), (x1 + tw + 4, y1), box_color, -1)
            cv2.putText(frame, label, (x1 + 2, y1 - 4), font, font_scale, (255, 255, 255), thickness)

    @property
    def is_available(self) -> bool:
        """Whether the detector is ready."""
        return self._model is not None

    @property
    def class_names(self) -> dict:
        """Mapping of class IDs to names."""
        return self._class_names

    @property
    def confidence_threshold(self) -> float:
        """Current confidence threshold."""
        return self._confidence_threshold


# Quick test when run directly
if __name__ == "__main__":
    import cv2
    import time

    print("ObjectDetector Module Test")
    print("=" * 40)

    detector = ObjectDetector()

    if not detector.is_available:
        print("\nDetector not available. Install ultralytics: pip install ultralytics")
        exit(1)

    print(f"\nDetectable classes: {len(detector.class_names)}")
    print(f"Confidence threshold: {detector.confidence_threshold:.0%}")

    print("\nStarting webcam test (press 'q' to quit)...")
    cap = cv2.VideoCapture(0)

    fps_start = time.time()
    fps_count = 0
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        detections = detector.detect(frame)
        detector.draw_detections(frame, detections)

        # FPS counter
        fps_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            fps = fps_count / elapsed
            fps_count = 0
            fps_start = time.time()

        cv2.putText(frame, f"FPS: {fps:.1f} | Objects: {len(detections)}",
                    (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)

        cv2.imshow("AIVA ObjectDetector Test", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
