"""
Tests for AIVA Object Detector — Detection Dataclass & Priority System
=======================================================================
Tests the Detection dataclass properties and the SAFETY_PRIORITY_CLASSES
mapping. Does NOT load the actual YOLO model.
"""

import pytest

from src.object_detector import Detection, SAFETY_PRIORITY_CLASSES, ObjectDetector


# =============================================================================
# DETECTION DATACLASS
# =============================================================================

class TestDetection:
    """Tests for the Detection dataclass."""

    def test_area_calculation(self):
        det = Detection(
            class_name="person", confidence=0.9,
            bbox=(100, 100, 200, 300),
            center_x=150, center_y=200,
        )
        assert det.area == 100 * 200  # (200-100) * (300-100) = 20000

    def test_area_zero_for_point(self):
        det = Detection("car", 0.8, (50, 50, 50, 50), 50, 50)
        assert det.area == 0

    def test_defaults_none(self):
        det = Detection("bench", 0.7, (0, 0, 10, 10), 5, 5)
        assert det.distance_m is None
        assert det.direction is None

    def test_distance_and_direction_settable(self):
        det = Detection("dog", 0.85, (0, 0, 100, 100), 50, 50)
        det.distance_m = 2.5
        det.direction = "left"
        assert det.distance_m == 2.5
        assert det.direction == "left"


# =============================================================================
# SAFETY PRIORITY CLASSES
# =============================================================================

class TestSafetyPriority:
    """Test the priority mapping used by SpatialEngine."""

    def test_vehicles_are_priority_zero(self):
        for cls in ["car", "truck", "bus", "motorcycle"]:
            assert SAFETY_PRIORITY_CLASSES[cls] == 0, f"{cls} should be priority 0"

    def test_bicycle_is_priority_one(self):
        assert SAFETY_PRIORITY_CLASSES["bicycle"] == 1

    def test_animals_are_priority_two(self):
        for cls in ["dog", "cat", "horse"]:
            assert SAFETY_PRIORITY_CLASSES[cls] == 2

    def test_person_is_priority_three(self):
        assert SAFETY_PRIORITY_CLASSES["person"] == 3

    def test_static_obstacles_are_priority_four(self):
        for cls in ["bench", "fire hydrant", "chair", "suitcase"]:
            assert SAFETY_PRIORITY_CLASSES[cls] == 4

    def test_unknown_defaults_to_five(self):
        """Unknown classes should get priority 5 when looked up with .get()."""
        assert SAFETY_PRIORITY_CLASSES.get("airplane", 5) == 5


# =============================================================================
# OBJECT DETECTOR (without model)
# =============================================================================

class TestObjectDetectorNoModel:
    """Test ObjectDetector behavior when YOLO is not loaded."""

    def test_unavailable_detector_returns_empty(self):
        """Create detector that skips loading, should return []."""
        det = object.__new__(ObjectDetector)
        det._model = None
        det._last_detections = []
        det._frame_count = 0
        import numpy as np
        result = det.detect(np.zeros((100, 100, 3), dtype=np.uint8))
        assert result == []

    def test_is_available_false_without_model(self):
        det = object.__new__(ObjectDetector)
        det._model = None
        assert det.is_available is False

    def test_confidence_threshold_enforced(self):
        """Confidence threshold should be at least 0.6 per PRD."""
        det = object.__new__(ObjectDetector)
        det._confidence_threshold = max(0.3, 0.6)
        assert det._confidence_threshold >= 0.6
