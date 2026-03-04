"""
Tests for AIVA Accuracy Improvements
=========================================
Tests temporal detection smoothing (DetectionTracker)
and frame quality validation.
"""

import numpy as np
import pytest
from unittest.mock import MagicMock

from src.object_detector import Detection, DetectionTracker


# =============================================================================
# HELPER
# =============================================================================

def _det(cls: str, direction: str = "center", conf: float = 0.85) -> Detection:
    """Create a test detection."""
    return Detection(
        class_name=cls,
        confidence=conf,
        bbox=(100, 100, 200, 200),
        center_x=150,
        center_y=150,
        direction=direction,
    )


# =============================================================================
# DETECTION TRACKER — TEMPORAL SMOOTHING
# =============================================================================

class TestDetectionTracker:
    """Test multi-frame confirmation / expire logic."""

    def test_single_frame_non_safety_filtered(self):
        """Non-safety objects seen in only 1 frame should NOT be reported."""
        tracker = DetectionTracker(confirm_frames=2, expire_frames=3)
        result = tracker.smooth([_det("chair", "left")])
        assert len(result) == 0  # Not yet confirmed

    def test_two_frames_confirms_non_safety(self):
        """Non-safety objects seen in 2 frames should be confirmed."""
        tracker = DetectionTracker(confirm_frames=2, expire_frames=3)
        tracker.smooth([_det("chair", "left")])  # Frame 1
        result = tracker.smooth([_det("chair", "left")])  # Frame 2
        assert len(result) == 1
        assert result[0].class_name == "chair"

    def test_safety_object_immediate(self):
        """Safety-critical objects (car, truck, bus) confirmed immediately."""
        tracker = DetectionTracker(confirm_frames=2, expire_frames=3)
        result = tracker.smooth([_det("car", "right")])
        assert len(result) == 1  # Immediately confirmed
        assert result[0].class_name == "car"

    def test_truck_immediate(self):
        tracker = DetectionTracker(confirm_frames=2)
        result = tracker.smooth([_det("truck", "center")])
        assert len(result) == 1

    def test_bus_immediate(self):
        tracker = DetectionTracker(confirm_frames=2)
        result = tracker.smooth([_det("bus", "left")])
        assert len(result) == 1

    def test_motorcycle_immediate(self):
        tracker = DetectionTracker(confirm_frames=2)
        result = tracker.smooth([_det("motorcycle", "right")])
        assert len(result) == 1

    def test_object_persists_after_disappearing(self):
        """Object should persist for expire_frames after disappearing."""
        tracker = DetectionTracker(confirm_frames=1, expire_frames=3)
        tracker.smooth([_det("person", "center")])  # Confirmed
        # Person disappears
        result1 = tracker.smooth([])  # Miss 1
        assert len(result1) == 1  # Still persists
        result2 = tracker.smooth([])  # Miss 2
        assert len(result2) == 1  # Still persists
        result3 = tracker.smooth([])  # Miss 3 = expired
        assert len(result3) == 0  # Gone

    def test_object_reappears_before_expire(self):
        """Object that reappears before expire should stay confirmed."""
        tracker = DetectionTracker(confirm_frames=1, expire_frames=3)
        tracker.smooth([_det("person", "center")])  # Confirmed
        tracker.smooth([])  # Miss 1
        tracker.smooth([])  # Miss 2
        result = tracker.smooth([_det("person", "center")])  # Reappears!
        assert len(result) == 1  # Still there

    def test_multiple_objects_tracked_independently(self):
        """Multiple objects are tracked separately by class+direction."""
        tracker = DetectionTracker(confirm_frames=2, expire_frames=3)
        tracker.smooth([
            _det("car", "left"),       # Safety: immediate
            _det("chair", "right"),    # Non-safety: needs confirmation
        ])
        result = tracker.smooth([
            _det("car", "left"),
            _det("chair", "right"),
        ])
        assert len(result) == 2  # Car was immediate, chair now confirmed

    def test_same_class_different_directions(self):
        """Same class in different directions tracked separately."""
        tracker = DetectionTracker(confirm_frames=2, expire_frames=3)
        tracker.smooth([_det("person", "left"), _det("person", "right")])
        result = tracker.smooth([_det("person", "left"), _det("person", "right")])
        assert len(result) == 2

    def test_higher_confidence_preferred(self):
        """If same key appears twice, higher confidence wins."""
        tracker = DetectionTracker(confirm_frames=1, expire_frames=3)
        # Two persons at center with different confidences
        d1 = _det("person", "center", 0.70)
        d2 = _det("person", "center", 0.95)
        result = tracker.smooth([d1, d2])
        assert len(result) == 1
        assert result[0].confidence == 0.95

    def test_reset_clears_all(self):
        """Reset should clear all tracks."""
        tracker = DetectionTracker(confirm_frames=1)
        tracker.smooth([_det("car", "center")])
        assert len(tracker.smooth([])) == 1  # Car persists
        tracker.reset()
        assert len(tracker.smooth([])) == 0  # All cleared

    def test_empty_input(self):
        """Empty detections should return empty."""
        tracker = DetectionTracker()
        assert tracker.smooth([]) == []


# =============================================================================
# FRAME QUALITY VALIDATION
# =============================================================================

class TestFrameQuality:
    """Test frame quality checks."""

    def _get_processor(self):
        """Create a minimal frame processor for quality testing."""
        from unittest.mock import patch
        # We only need the _check_frame_quality method,
        # so we mock out __init__
        from server.frame_processor import FrameProcessor
        with patch.object(FrameProcessor, '__init__', lambda self: None):
            proc = FrameProcessor()
        return proc

    def test_normal_frame_passes(self):
        proc = self._get_processor()
        # Create a normal frame with texture (not blurry, not dark)
        frame = np.random.randint(40, 200, (480, 640, 3), dtype=np.uint8)
        ok, reason = proc._check_frame_quality(frame)
        assert ok is True

    def test_black_frame_rejected(self):
        proc = self._get_processor()
        frame = np.zeros((480, 640, 3), dtype=np.uint8)  # Fully black
        ok, reason = proc._check_frame_quality(frame)
        assert ok is False
        assert "dark" in reason.lower()

    def test_white_frame_rejected(self):
        proc = self._get_processor()
        frame = np.full((480, 640, 3), 250, dtype=np.uint8)  # Fully white
        ok, reason = proc._check_frame_quality(frame)
        assert ok is False
        assert "overexposed" in reason.lower()

    def test_blurry_frame_rejected(self):
        proc = self._get_processor()
        # Uniform gray = zero Laplacian variance = maximally blurry
        frame = np.full((480, 640, 3), 128, dtype=np.uint8)
        ok, reason = proc._check_frame_quality(frame)
        assert ok is False
        assert "blur" in reason.lower()

    def test_textured_bright_frame_passes(self):
        proc = self._get_processor()
        # Checkerboard pattern = high Laplacian variance = sharp
        frame = np.zeros((480, 640, 3), dtype=np.uint8)
        frame[::2, ::2] = 200
        frame[1::2, 1::2] = 200
        ok, reason = proc._check_frame_quality(frame)
        assert ok is True
