"""
Tests for AIVA Frame Processor — Pipeline Routing Tests (Mocked Models)
========================================================================
Tests the FrameProcessor pipeline logic by mocking all heavy dependencies
(YOLO, MiDaS, OCR, face_recognition). No 500MB+ models are loaded.
"""

import time
import pytest
import numpy as np
from unittest.mock import MagicMock, patch, PropertyMock
from dataclasses import dataclass

from server.protocol import MessageType, FrameResponse
from server.frame_processor import ClientState

@pytest.fixture
def dummy_frame():
    # Use a frame with realistic brightness & texture to pass quality checks
    # (Uniform black/white frames are rejected by the frame quality gate)
    np.random.seed(42)
    return np.random.randint(40, 200, (480, 640, 3), dtype=np.uint8)

@pytest.fixture
def dummy_state():
    return ClientState(client_id="test_client")


# =============================================================================
# HELPERS — Create a FrameProcessor with all models mocked
# =============================================================================

def _build_mock_processor():
    """
    Build a FrameProcessor instance with all external models mocked out.
    
    This avoids loading YOLO (~6MB), MiDaS (~50MB), EasyOCR (~100MB+),
    and face_recognition/dlib models.
    """
    from server.frame_processor import FrameProcessor
    from src.object_detector import Detection

    proc = object.__new__(FrameProcessor)

    # Mock detector
    proc._detector = MagicMock()
    proc._detector.is_available = True
    proc._detector.detect.return_value = [
        Detection(
            class_name="person", confidence=0.85,
            bbox=(100, 100, 200, 300), center_x=150, center_y=200,
        ),
    ]

    # Mock depth estimator
    proc._depth = MagicMock()
    proc._depth.is_available = True
    proc._depth.estimate.return_value = np.full((480, 640), 3.0, dtype=np.float32)
    proc._depth.enrich_detections = MagicMock()

    # Mock spatial engine (use real one since it's pure logic)
    from src.spatial_engine import SpatialEngine
    proc._spatial = SpatialEngine(warning_cooldown=0)

    # Mock OCR
    proc._ocr = MagicMock()
    proc._ocr.is_available = True
    proc._ocr.read.return_value = ("Hello World", 50.0)

    # No face detector
    proc._face_detector = None

    return proc


# =============================================================================
# PIPELINE ROUTING
# =============================================================================

class TestPipelineRouting:
    """Test that process() routes correctly by MessageType."""

    def test_detect_route_calls_yolo(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_DETECT, dummy_state, frame_id=1)
        assert resp.frame_id == 1
        assert resp.type == "frame_result"
        proc._detector.detect.assert_called_once()

    def test_ocr_route_calls_ocr(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_OCR, dummy_state, frame_id=2)
        assert resp.ocr_text == "Hello World"
        proc._ocr.read.assert_called_once()

    def test_describe_route_returns_placeholder(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_DESCRIBE, dummy_state, frame_id=3)
        assert "Gemini" in resp.surroundings

    def test_latency_populated(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_DETECT, dummy_state)
        assert resp.latency_ms >= 0
        assert resp.timestamp_ms > 0


# =============================================================================
# DETECTION PIPELINE
# =============================================================================

class TestDetectionPipeline:
    """Test the detection → depth → spatial pipeline."""

    def test_detections_serialized(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_DETECT, dummy_state)
        assert len(resp.detections) >= 1
        assert resp.detections[0]["class"] == "person"

    def test_depth_enrich_called(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        # Pre-populate cached depth map so frame-skip path returns valid data.
        # Without this, _frame_count=1 mod MIDAS_FRAME_SKIP(3) != 0, so
        # estimate() isn't called and cached=None → enrich skipped.
        dummy_state.cached_depth_map = np.full((100, 100), 3.0, dtype=np.float32)
        proc.process(dummy_frame, MessageType.FRAME_DETECT, dummy_state)
        proc._depth.enrich_detections.assert_called()

    def test_surroundings_populated(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        resp = proc.process(dummy_frame, MessageType.FRAME_DETECT, dummy_state)
        assert resp.surroundings is not None


# =============================================================================
# OCR PIPELINE
# =============================================================================

class TestOCRPipeline:
    """Test the OCR branch."""

    def test_ocr_unavailable_message(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        proc._ocr.is_available = False
        resp = proc.process(dummy_frame, MessageType.FRAME_OCR, dummy_state)
        assert resp.ocr_text == "OCR engine not available."

    def test_ocr_no_text(self, dummy_frame, dummy_state):
        proc = _build_mock_processor()
        proc._ocr.read.return_value = (None, 30.0)
        resp = proc.process(dummy_frame, MessageType.FRAME_OCR, dummy_state)
        assert resp.ocr_text == "No text detected."


# =============================================================================
# MOTION DELTA SAFETY
# =============================================================================

class TestMotionDelta:
    """Test the motion-delta safety override for depth estimation."""

    def test_no_previous_frame_no_force(self, dummy_state):
        proc = _build_mock_processor()
        dummy_state.prev_detection_areas = {}
        from src.object_detector import Detection
        dets = [Detection("car", 0.9, (100, 100, 200, 200), 150, 150)]
        force = proc._check_motion_delta(dets, dummy_state)
        assert force is False

    def test_rapid_growth_forces_depth(self, dummy_state):
        proc = _build_mock_processor()
        dummy_state.prev_detection_areas = {"car": 1000}
        from src.object_detector import Detection
        # Area = 200*200 = 40000 → 40000/1000 = 40x growth >> 1.4 threshold
        dets = [Detection("car", 0.9, (100, 100, 300, 300), 200, 200)]
        force = proc._check_motion_delta(dets, dummy_state)
        assert force is True

    def test_small_change_no_force(self, dummy_state):
        proc = _build_mock_processor()
        dummy_state.prev_detection_areas = {"person": 10000}
        from src.object_detector import Detection
        # Area = 10100 → 10100/10000 = 1.01x < 1.4 threshold
        dets = [Detection("person", 0.8, (100, 100, 201, 200), 150, 150)]
        force = proc._check_motion_delta(dets, dummy_state)
        assert force is False


# =============================================================================
# STATUS PROPERTIES
# =============================================================================

class TestProcessorStatus:
    """Test is_ready and models_status properties."""

    def test_is_ready_when_detector_available(self):
        proc = _build_mock_processor()
        assert proc.is_ready is True

    def test_not_ready_when_detector_unavailable(self):
        proc = _build_mock_processor()
        proc._detector.is_available = False
        assert proc.is_ready is False

    def test_models_status_dict(self):
        proc = _build_mock_processor()
        status = proc.models_status
        assert status["yolo"] is True
        assert status["midas"] is True
        assert status["ocr"] is True
        assert status["faces"] is False  # No face detector loaded
