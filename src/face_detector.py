"""
VASIS - Face Detector Module
============================
Local face recognition for privacy-first person identification.

This module loads known faces from a folder, encodes them on startup,
and provides real-time face detection and identification.
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np
# PIL no longer needed — dlib fix uses np.ascontiguousarray directly

try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("[FaceDetector] WARNING: face_recognition not installed.")
    print("  Install with: pip install face_recognition")
    print("  Windows users may need Visual Studio Build Tools with C++ workload.")


class FaceDetector:
    """
    Local face recognition using dlib's 128-dimensional face encodings.
    
    Faces are loaded from a folder on startup. The filename (without extension)
    becomes the person's name (e.g., 'mom.jpg' -> 'Mom').
    
    Usage:
        detector = FaceDetector(known_faces_dir="known_faces/")
        detector.load_known_faces()
        
        # In your main loop:
        faces = detector.detect_and_identify(frame)
        for name, (top, right, bottom, left) in faces:
            cv2.rectangle(frame, (left, top), (right, bottom), (0, 255, 0), 2)
            cv2.putText(frame, name, (left, top - 10), ...)
    """
    
    # Supported image extensions
    VALID_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.bmp', '.gif'}
    
    def __init__(
        self, 
        known_faces_dir: str = "known_faces",
        tolerance: float = 0.6,
        frame_skip: int = 10,
        detection_model: str = "hog"
    ):
        """
        Initialize the face detector.
        
        Args:
            known_faces_dir: Path to folder containing known face images
            tolerance: How strict the matching is (lower = stricter, default 0.6)
            frame_skip: Process every Nth frame to save CPU
            detection_model: 'hog' (faster, CPU) or 'cnn' (accurate, GPU)
        """
        self.known_faces_dir = Path(known_faces_dir)
        self.tolerance = tolerance
        self.frame_skip = frame_skip
        self.detection_model = detection_model
        
        # Known face data
        self._known_encodings: List[np.ndarray] = []
        self._known_names: List[str] = []
        
        # State
        self._frame_count = 0
        self._current_person_visible: str = "No one"
        self._last_faces: List[Tuple[str, Tuple[int, int, int, int]]] = []
        
        # Dlib fallback mode - uses OpenCV cascade when dlib fails
        self._use_opencv_fallback = False
        self._opencv_face_cascade = None
        self._opencv_recognizer = None  # LBPH face recognizer
        self._opencv_label_map = {}  # Maps label ID to name
        
        # Check if library is available
        if not FACE_RECOGNITION_AVAILABLE:
            print("[FaceDetector] Face recognition disabled - library not available")
        
        # Pre-load OpenCV cascade as a backup
        try:
            cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            self._opencv_face_cascade = cv2.CascadeClassifier(cascade_path)
            if self._opencv_face_cascade.empty():
                self._opencv_face_cascade = None
            else:
                # Initialize LBPH recognizer for face matching
                self._opencv_recognizer = cv2.face.LBPHFaceRecognizer_create()
        except Exception as e:
            self._opencv_face_cascade = None
            print(f"[FaceDetector] OpenCV cascade init error: {e}")
    
    def load_known_faces(self) -> int:
        """
        Load and encode all faces from the known_faces directory.
        
        Returns:
            Number of faces successfully loaded
        
        Raises:
            FileNotFoundError: If known_faces_dir doesn't exist
        """
        if not self.known_faces_dir.exists():
            print(f"[FaceDetector] Creating known_faces directory: {self.known_faces_dir}")
            self.known_faces_dir.mkdir(parents=True, exist_ok=True)
            return 0
        
        self._known_encodings = []
        self._known_names = []
        
        # For OpenCV LBPH recognizer
        opencv_faces = []
        opencv_labels = []
        self._opencv_label_map = {}
        
        print(f"[FaceDetector] Loading faces from: {self.known_faces_dir}")
        
        # Find all image files
        image_files = [
            f for f in self.known_faces_dir.iterdir()
            if f.is_file() and f.suffix.lower() in self.VALID_EXTENSIONS
        ]
        
        if not image_files:
            print("[FaceDetector] No face images found. Add images to known_faces/")
            return 0
        
        loaded_count = 0
        for image_path in image_files:
            try:
                # Extract name from filename (without extension)
                name = image_path.stem.replace('_', ' ').title()
                
                # Load image with OpenCV for LBPH training
                cv_img = cv2.imread(str(image_path))
                if cv_img is None:
                    print(f"  ✗ Could not load: {image_path.name}")
                    continue
                
                gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
                
                # Detect face in the known face image using cascade
                if self._opencv_face_cascade is not None:
                    faces = self._opencv_face_cascade.detectMultiScale(
                        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
                    )
                    
                    if len(faces) > 0:
                        # Use the first (largest) face
                        x, y, w, h = faces[0]
                        face_roi = gray[y:y+h, x:x+w]
                        face_roi = cv2.resize(face_roi, (100, 100))  # Normalize size
                        
                        label_id = loaded_count
                        opencv_faces.append(face_roi)
                        opencv_labels.append(label_id)
                        self._opencv_label_map[label_id] = name
                        self._known_names.append(name)
                        loaded_count += 1
                        print(f"  ✓ Loaded: {name}")
                    else:
                        print(f"  ✗ No face found in: {image_path.name}")
                else:
                    print(f"  ✗ OpenCV cascade not available")
                    
            except Exception as e:
                print(f"  ✗ Error loading {image_path.name}: {e}")
        
        # Train the OpenCV LBPH recognizer
        if opencv_faces and self._opencv_recognizer is not None:
            try:
                self._opencv_recognizer.train(opencv_faces, np.array(opencv_labels))
                print(f"[FaceDetector] LBPH recognizer trained with {loaded_count} face(s)")
            except Exception as e:
                print(f"[FaceDetector] LBPH training failed: {e}")
        
        print(f"[FaceDetector] Loaded {loaded_count} known face(s)")
        return loaded_count
    
    def detect_and_identify(
        self, 
        frame: np.ndarray,
        force: bool = False
    ) -> List[Tuple[str, Tuple[int, int, int, int]]]:
        """
        Detect and identify faces in a frame.
        
        Args:
            frame: BGR image from OpenCV
            force: If True, process even if frame_skip hasn't elapsed
        
        Returns:
            List of (name, (top, right, bottom, left)) tuples
        """
        if not FACE_RECOGNITION_AVAILABLE:
            return []
        
        # Frame skipping for CPU efficiency
        self._frame_count += 1
        if not force and self._frame_count % self.frame_skip != 0:
            return self._last_faces
        
        try:
            # 1. Ensure input is valid
            if frame is None or frame.size == 0:
                return self._last_faces
            
            # 2. Validate and sanitize input frame
            if frame.dtype != np.uint8:
                frame = frame.astype(np.uint8)
            
            # Ensure frame is 3-channel BGR
            if len(frame.shape) == 2:
                # Grayscale - convert to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
            elif len(frame.shape) == 3 and frame.shape[2] == 4:
                # BGRA - convert to BGR
                frame = cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
            elif len(frame.shape) != 3 or frame.shape[2] != 3:
                # Unsupported format, skip this frame
                return self._last_faces

            # 3. Resize for faster processing (0.25 scale)
            small_bgr = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            
            face_locations = []
            face_encodings = []
            
            # Try dlib first (if not already in fallback mode)
            if not self._use_opencv_fallback:
                try:
                    # Direct conversion: BGR→RGB + enforce C-contiguous uint8.
                    # dlib's internal check requires is_row_major_order on the
                    # raw buffer. cv2.resize() can produce non-contiguous arrays
                    # on Windows, causing RuntimeError: Unsupported image type.
                    # np.ascontiguousarray is a no-op if already contiguous.
                    small_rgb = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2RGB)
                    small_rgb = np.ascontiguousarray(small_rgb, dtype=np.uint8)
                    
                    face_locations = face_recognition.face_locations(
                        small_rgb, 
                        model=self.detection_model
                    )
                    
                    if face_locations:
                        face_encodings = face_recognition.face_encodings(small_rgb, face_locations)
                        
                except RuntimeError as dl_err:
                    if "Unsupported image type" in str(dl_err):
                        print("[FaceDetector] Switching to OpenCV cascade (dlib incompatible)")
                        self._use_opencv_fallback = True
            
            # Use OpenCV cascade fallback with LBPH recognition
            if self._use_opencv_fallback and self._opencv_face_cascade is not None:
                gray = cv2.cvtColor(small_bgr, cv2.COLOR_BGR2GRAY)
                detections = self._opencv_face_cascade.detectMultiScale(
                    gray, 
                    scaleFactor=1.1, 
                    minNeighbors=5, 
                    minSize=(20, 20)
                )
                
                # Convert OpenCV format (x, y, w, h) to face_recognition format (top, right, bottom, left)
                # and try to recognize each face using LBPH
                for (x, y, w, h) in detections:
                    top = y
                    right = x + w
                    bottom = y + h
                    left = x
                    face_locations.append((top, right, bottom, left))
                    
                    # Try to recognize the face using LBPH
                    recognized_name = None
                    if self._opencv_recognizer is not None and self._opencv_label_map:
                        try:
                            face_roi = gray[y:y+h, x:x+w]
                            face_roi = cv2.resize(face_roi, (100, 100))
                            label, confidence = self._opencv_recognizer.predict(face_roi)
                            # LBPH confidence: lower is better, typically < 80 is a good match
                            if confidence < 80:
                                recognized_name = self._opencv_label_map.get(label, None)
                        except Exception:
                            pass
                    
                    face_encodings.append(recognized_name)  # Store name instead of encoding
                
            if not face_locations:
                self._current_person_visible = "No one"
                self._last_faces = []
                if hasattr(self, '_last_error'): delattr(self, '_last_error')
                return []
            
            results = []
            names_found = []
            
            for i, (top, right, bottom, left) in enumerate(face_locations):
                # Scale back up (we resized to 0.25)
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                # Try to match with known faces
                name = "Unknown"
                
                if i < len(face_encodings) and face_encodings[i] is not None:
                    encoding_or_name = face_encodings[i]
                    
                    # Check if it's already a recognized name (from LBPH) or a dlib encoding
                    if isinstance(encoding_or_name, str):
                        # LBPH recognized name
                        name = encoding_or_name
                    elif isinstance(encoding_or_name, np.ndarray) and self._known_encodings:
                        # Dlib encoding - compare to known faces
                        distances = face_recognition.face_distance(
                            self._known_encodings, 
                            encoding_or_name
                        )
                        
                        if len(distances) > 0:
                            best_match_idx = np.argmin(distances)
                            if distances[best_match_idx] <= self.tolerance:
                                name = self._known_names[best_match_idx]
                
                results.append((name, (top, right, bottom, left)))
                names_found.append(name)
            
            # Update current person visible (prefer known names)
            known_names = [n for n in names_found if n != "Unknown"]
            if known_names:
                self._current_person_visible = known_names[0]
            elif names_found:
                self._current_person_visible = "Unknown person"
            else:
                self._current_person_visible = "No one"
            
            self._last_faces = results
            # Clear error suppression on success
            if hasattr(self, '_last_error'): delattr(self, '_last_error')
            return results
            
        except Exception as e:
            # Suppress repetitive errors
            current_error = str(e)
            if not hasattr(self, '_last_error') or self._last_error != current_error:
                print(f"[FaceDetector] Warning: {current_error}")
                self._last_error = current_error
            return self._last_faces
    
    @property
    def current_person_visible(self) -> str:
        """The last detected person's name."""
        return self._current_person_visible
    
    @property
    def known_face_count(self) -> int:
        """Number of known faces loaded."""
        return len(self._known_names)
    
    @property
    def known_names(self) -> List[str]:
        """List of all known face names."""
        return self._known_names.copy()


def draw_face_boxes(
    frame: np.ndarray, 
    faces: List[Tuple[str, Tuple[int, int, int, int]]],
    known_color: Tuple[int, int, int] = (0, 255, 0),
    unknown_color: Tuple[int, int, int] = (0, 165, 255)
) -> None:
    """
    Draw bounding boxes and names on detected faces.
    
    Args:
        frame: The frame to draw on (modified in place)
        faces: List of (name, (top, right, bottom, left)) from detect_and_identify
        known_color: BGR color for known faces (default: green)
        unknown_color: BGR color for unknown faces (default: orange)
    """
    for name, (top, right, bottom, left) in faces:
        # Choose color based on known/unknown
        color = known_color if name != "Unknown" else unknown_color
        
        # Draw box
        cv2.rectangle(frame, (left, top), (right, bottom), color, 2)
        
        # Draw name label with background
        label = name
        font = cv2.FONT_HERSHEY_SIMPLEX
        font_scale = 0.6
        thickness = 2
        
        # Get text size for background
        (text_width, text_height), baseline = cv2.getTextSize(
            label, font, font_scale, thickness
        )
        
        # Draw label background
        cv2.rectangle(
            frame,
            (left, top - text_height - 10),
            (left + text_width + 10, top),
            color,
            -1  # Filled
        )
        
        # Draw text
        cv2.putText(
            frame,
            label,
            (left + 5, top - 5),
            font,
            font_scale,
            (255, 255, 255),  # White text
            thickness
        )


# Quick test when run directly
if __name__ == "__main__":
    print("FaceDetector Module Test")
    print("=" * 40)
    
    if not FACE_RECOGNITION_AVAILABLE:
        print("\nface_recognition library not available.")
        print("Install with: pip install face_recognition")
        exit(1)
    
    detector = FaceDetector(known_faces_dir="known_faces")
    count = detector.load_known_faces()
    
    print(f"\nLoaded {count} known faces: {detector.known_names}")
    
    # Test with webcam
    print("\nStarting webcam test (press 'q' to quit)...")
    cap = cv2.VideoCapture(0)
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        
        faces = detector.detect_and_identify(frame, force=True)
        draw_face_boxes(frame, faces)
        
        # Show current person
        cv2.putText(
            frame,
            f"Visible: {detector.current_person_visible}",
            (10, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.8,
            (0, 255, 0),
            2
        )
        
        cv2.imshow("Face Detection Test", frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
