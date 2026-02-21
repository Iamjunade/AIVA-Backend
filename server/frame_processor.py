"""
AIVA Server — Frame Processor
================================
Pipeline orchestrator that converts JPEG frames into structured JSON responses.

Pipeline stages:
    1. JPEG decode → numpy array
    2. YOLOv8 Nano object detection
    3. MiDaS depth estimation (with frame-skip + motion-delta safety)
    4. Spatial intelligence (dual-threshold warnings)
    5. EasyOCR (user-triggered only, never auto-invoked)
    6. Face recognition (optional)
    7. JSON response construction

Every stage is timed. If any stage exceeds its latency budget,
a warning is logged and the pipeline proceeds with partial data.

Motion-Delta Safety Check:
    If any detected object's bounding box area grows by >40% between frames,
    depth estimation is forced immediately (bypasses frame-skip) because
    a fast-approaching object requires fresh distance data.
"""

import time
import logging
from typing import Dict, List, Optional, Tuple

import cv2
import numpy as np

from src.object_detector import ObjectDetector, Detection
from src.depth_estimator import DepthEstimator
from src.spatial_engine import SpatialEngine

from server.config import (
    YOLO_MODEL,
    YOLO_CONFIDENCE,
    YOLO_IMG_SIZE,
    MIDAS_MODEL,
    MIDAS_DEPTH_SCALE,
    MIDAS_FRAME_SKIP,
    MIDAS_MOTION_DELTA_THRESHOLD,
    CAUTION_DISTANCE_M,
    DANGER_DISTANCE_M,
    PROCESSING_TIMEOUT_MS,
    LATENCY_BUDGET_YOLO_MS,
    LATENCY_BUDGET_MIDAS_MS,
    LATENCY_BUDGET_OCR_MS,
)
from server.ocr_engine import OCREngine
from server.protocol import (
    FrameResponse,
    WarningResult,
    DetectionResult,
    MessageType,
)


logger = logging.getLogger("aiva.processor")


class FrameProcessor:
    """
    Processes JPEG frames through the AIVA vision pipeline.

    Thread-safe: designed to be called from an async WebSocket handler.
    All state (models, caches) is managed internally.

    Usage:
        processor = FrameProcessor()
        result = processor.process(jpeg_bytes, MessageType.FRAME_DETECT)
    """

    def __init__(self):
        """
        Initialize all vision models.

        Model loading happens here (takes several seconds on first run).
        After initialization, is_ready indicates whether all critical
        models loaded successfully.
        """
        logger.info("Initializing AIVA frame processor...")
        start = time.time()

        # Stage 1: Object detection
        self._detector = ObjectDetector(
            model_name=YOLO_MODEL,
            confidence_threshold=YOLO_CONFIDENCE,
            img_size=YOLO_IMG_SIZE,
        )

        # Stage 2: Depth estimation
        self._depth = DepthEstimator(
            model_type=MIDAS_MODEL,
            depth_scale=MIDAS_DEPTH_SCALE,
        )

        # Stage 3: Spatial engine (dual-threshold)
        self._spatial = SpatialEngine(
            caution_distance=CAUTION_DISTANCE_M,
            danger_distance=DANGER_DISTANCE_M,
        )

        # Stage 4: OCR (loaded but ONLY triggered by FRAME_OCR requests)
        self._ocr = OCREngine()

        # Stage 5: Face recognition (optional, loaded separately)
        self._face_detector = None
        self._load_face_detector()

        # Frame-skip state for MiDaS
        self._frame_count = 0
        self._cached_depth_map: Optional[np.ndarray] = None
        self._cached_frame_width: int = 0

        # Motion-delta state: track previous frame's detection areas
        self._prev_detection_areas: Dict[str, float] = {}

        elapsed = (time.time() - start) * 1000
        logger.info(f"Frame processor initialized in {elapsed:.0f}ms")
        logger.info(f"  YOLO: {'ready' if self._detector.is_available else 'FAILED'}")
        logger.info(f"  MiDaS: {'ready' if self._depth.is_available else 'FAILED'}")
        logger.info(f"  OCR: {'ready' if self._ocr.is_available else 'FAILED'}")
        logger.info(f"  Faces: {'ready' if self._face_detector else 'disabled'}")

    def _load_face_detector(self) -> None:
        """Load face detector if available."""
        try:
            from src.face_detector import FaceDetector
            self._face_detector = FaceDetector()
            if not self._face_detector.known_count:
                logger.info("Face detector loaded but no known faces registered")
        except Exception as e:
            logger.warning(f"Face detector not available: {e}")
            self._face_detector = None

    # =========================================================================
    # PUBLIC INTERFACE
    # =========================================================================

    def process(
        self,
        jpeg_bytes: bytes,
        msg_type: MessageType,
        frame_id: int = 0,
    ) -> FrameResponse:
        """
        Process a JPEG frame through the vision pipeline.

        Args:
            jpeg_bytes: Raw JPEG image bytes from the mobile client
            msg_type: Type of processing requested
            frame_id: Client-assigned frame identifier

        Returns:
            FrameResponse with detections, warnings, and optional OCR/faces
        """
        pipeline_start = time.time()
        response = FrameResponse(frame_id=frame_id)
        timings: Dict[str, float] = {}

        # Stage 0: Decode JPEG
        frame = self._decode_jpeg(jpeg_bytes)
        if frame is None:
            response.type = "error"
            response.danger_summary = "Frame decode failed"
            return response

        frame_width = frame.shape[1]

        # Route to appropriate processing pipeline
        if msg_type == MessageType.FRAME_DETECT:
            self._process_detection(frame, frame_width, response, timings)

        elif msg_type == MessageType.FRAME_OCR:
            self._process_ocr(frame, response, timings)

        elif msg_type == MessageType.FRAME_DESCRIBE:
            # Scene description via Gemini (deferred — not in navigation loop)
            response.surroundings = "Scene description requires Gemini API (not in navigation loop)."

        # Face recognition (runs on all frame types)
        if self._face_detector is not None:
            self._process_faces(frame, response, timings)

        # Finalize timing
        total_ms = (time.time() - pipeline_start) * 1000
        response.latency_ms = int(total_ms)
        response.timestamp_ms = int(time.time() * 1000)

        # Log latency budget
        if total_ms > PROCESSING_TIMEOUT_MS:
            logger.warning(
                f"Frame {frame_id} exceeded budget: {total_ms:.0f}ms "
                f"(limit {PROCESSING_TIMEOUT_MS}ms) | stages: {timings}"
            )
        else:
            logger.debug(
                f"Frame {frame_id}: {total_ms:.0f}ms | stages: {timings}"
            )

        return response

    # =========================================================================
    # PIPELINE STAGES
    # =========================================================================

    def _decode_jpeg(self, jpeg_bytes: bytes) -> Optional[np.ndarray]:
        """
        Decode JPEG bytes to OpenCV BGR frame.

        Args:
            jpeg_bytes: Raw JPEG bytes

        Returns:
            BGR numpy array or None on failure
        """
        try:
            arr = np.frombuffer(jpeg_bytes, dtype=np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None or frame.size == 0:
                logger.error("JPEG decode returned empty frame")
                return None
            return frame
        except Exception as e:
            logger.error(f"JPEG decode error: {e}")
            return None

    def _process_detection(
        self,
        frame: np.ndarray,
        frame_width: int,
        response: FrameResponse,
        timings: Dict[str, float],
    ) -> None:
        """
        Run object detection + depth + spatial pipeline.

        Steps:
            1. YOLOv8 detection
            2. MiDaS depth (with frame-skip + motion-delta safety)
            3. Spatial analysis (dual-threshold warnings)
        """
        # --- Stage 1: Object Detection ---
        t0 = time.time()
        detections = self._detector.detect(frame) if self._detector.is_available else []
        yolo_ms = (time.time() - t0) * 1000
        timings["yolo_ms"] = round(yolo_ms, 1)

        if yolo_ms > LATENCY_BUDGET_YOLO_MS:
            logger.warning(f"YOLO exceeded budget: {yolo_ms:.0f}ms > {LATENCY_BUDGET_YOLO_MS}ms")

        # --- Stage 2: Depth Estimation (with motion-delta safety) ---
        t1 = time.time()
        depth_map = self._get_depth_map(frame, detections)
        midas_ms = (time.time() - t1) * 1000
        timings["midas_ms"] = round(midas_ms, 1)

        # Enrich detections with distance and direction
        if depth_map is not None and self._depth.is_available:
            self._depth.enrich_detections(detections, depth_map, frame_width)

        # --- Stage 3: Spatial Analysis ---
        t2 = time.time()
        warnings = self._spatial.check_obstacles(detections)
        surroundings = self._spatial.get_surroundings(detections)
        danger_summary = self._spatial.get_danger_summary(detections)
        spatial_ms = (time.time() - t2) * 1000
        timings["spatial_ms"] = round(spatial_ms, 1)

        # Build response
        response.detections = [
            {
                "class": d.class_name,
                "confidence": round(d.confidence, 3),
                "distance_m": round(d.distance_m, 2) if d.distance_m else None,
                "direction": d.direction,
                "bbox": list(d.bbox),
            }
            for d in detections
        ]

        response.warnings = [
            {
                "message": w.message,
                "priority": w.priority,
                "is_critical": w.is_critical,
                "zone": w.zone,
            }
            for w in warnings
        ]

        response.surroundings = surroundings
        response.danger_summary = danger_summary

    def _get_depth_map(
        self,
        frame: np.ndarray,
        detections: List[Detection],
    ) -> Optional[np.ndarray]:
        """
        Get depth map with frame-skipping and motion-delta safety.

        Logic:
            1. Check if any object is approaching rapidly (area growth > 40%)
            2. If yes → force immediate depth estimation (safety override)
            3. If no → use cached depth if within skip interval
            4. Otherwise → run depth estimation normally

        Args:
            frame: BGR image
            detections: Current frame's detections

        Returns:
            Depth map (may be cached) or None
        """
        if not self._depth.is_available:
            return self._cached_depth_map

        self._frame_count += 1

        # Check motion delta: is anything approaching fast?
        force_depth = self._check_motion_delta(detections)

        if force_depth:
            logger.info("Motion-delta triggered: forcing depth estimation")

        # Run depth if: forced by motion OR frame-skip interval reached
        should_run = force_depth or (self._frame_count % MIDAS_FRAME_SKIP == 0)

        if should_run:
            t0 = time.time()
            depth_map = self._depth.estimate(frame)
            elapsed = (time.time() - t0) * 1000

            if elapsed > LATENCY_BUDGET_MIDAS_MS:
                logger.warning(f"MiDaS exceeded budget: {elapsed:.0f}ms > {LATENCY_BUDGET_MIDAS_MS}ms")

            if depth_map is not None:
                self._cached_depth_map = depth_map
                self._cached_frame_width = frame.shape[1]

            return depth_map
        else:
            # Use cached depth map
            return self._cached_depth_map

    def _check_motion_delta(self, detections: List[Detection]) -> bool:
        """
        Check if any detected object is approaching rapidly.

        Compares bounding box areas between current and previous frame.
        If any object's area grew by more than MIDAS_MOTION_DELTA_THRESHOLD
        (default 40%), returns True to force immediate depth estimation.

        This prevents stale depth data when a fast-moving object
        (vehicle, bicycle) is approaching the user.

        Args:
            detections: Current frame's detections

        Returns:
            True if immediate depth estimation is needed
        """
        current_areas: Dict[str, float] = {}
        force = False

        for det in detections:
            area = det.area
            key = det.class_name

            # Track largest instance of each class
            if key not in current_areas or area > current_areas[key]:
                current_areas[key] = area

            # Compare with previous frame
            if key in self._prev_detection_areas:
                prev_area = self._prev_detection_areas[key]
                if prev_area > 0:
                    growth = area / prev_area
                    if growth > MIDAS_MOTION_DELTA_THRESHOLD:
                        logger.debug(
                            f"Motion delta: {key} area grew {growth:.2f}x "
                            f"(threshold: {MIDAS_MOTION_DELTA_THRESHOLD}x)"
                        )
                        force = True

        # Update previous areas for next frame
        self._prev_detection_areas = current_areas

        return force

    def _process_ocr(
        self,
        frame: np.ndarray,
        response: FrameResponse,
        timings: Dict[str, float],
    ) -> None:
        """
        Run user-triggered OCR on a frame.

        Returns exact text as captured. No summarization.

        Args:
            frame: BGR image
            response: Response object to populate
            timings: Timing dict to update
        """
        if not self._ocr.is_available:
            response.ocr_text = "OCR engine not available."
            return

        t0 = time.time()
        text, ocr_ms = self._ocr.read(frame)
        total_ms = (time.time() - t0) * 1000
        timings["ocr_ms"] = round(total_ms, 1)

        if total_ms > LATENCY_BUDGET_OCR_MS:
            logger.warning(f"OCR exceeded budget: {total_ms:.0f}ms > {LATENCY_BUDGET_OCR_MS}ms")

        if text:
            response.ocr_text = text
        else:
            response.ocr_text = "No text detected."

    def _process_faces(
        self,
        frame: np.ndarray,
        response: FrameResponse,
        timings: Dict[str, float],
    ) -> None:
        """
        Run face recognition on a frame.

        Args:
            frame: BGR image
            response: Response object to populate
            timings: Timing dict to update
        """
        try:
            t0 = time.time()
            face_locations, face_names = self._face_detector.detect_known_faces(frame)
            face_ms = (time.time() - t0) * 1000
            timings["face_ms"] = round(face_ms, 1)

            # Only include recognized (non-Unknown) faces
            recognized = [name for name in face_names if name != "Unknown"]
            response.faces = recognized

        except Exception as e:
            logger.debug(f"Face recognition error: {e}")

    # =========================================================================
    # STATUS
    # =========================================================================

    @property
    def is_ready(self) -> bool:
        """
        Whether the processor is ready to handle frames.

        Requires at minimum the object detector to be loaded.
        MiDaS and OCR are optional but degraded without them.
        """
        return self._detector.is_available

    @property
    def models_status(self) -> Dict[str, bool]:
        """Status of each loaded model."""
        return {
            "yolo": self._detector.is_available,
            "midas": self._depth.is_available,
            "ocr": self._ocr.is_available,
            "faces": self._face_detector is not None,
        }
