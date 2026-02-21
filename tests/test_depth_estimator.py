"""
Tests for AIVA Depth Estimator — Pure Logic Tests (No Model Loading)
=====================================================================
Tests _normalize_depth, get_distance_at, get_direction, enrich_detections
using mock data. Does NOT load the actual MiDaS model.
"""

import pytest
import numpy as np

from src.depth_estimator import DepthEstimator
from src.object_detector import Detection


# =============================================================================
# HELPERS — Build estimator without loading torch/MiDaS
# =============================================================================

def _make_estimator() -> DepthEstimator:
    """Create a DepthEstimator with the model set to None (skip loading)."""
    est = object.__new__(DepthEstimator)
    est._model = None
    est._transform = None
    est._device = None
    est._depth_scale = 3.0
    est._last_depth_map = None
    est._frame_count = 0
    est.MAX_DEPTH_M = 15.0
    return est


# =============================================================================
# _normalize_depth
# =============================================================================

class TestNormalizeDepth:
    """Test the raw → metric depth conversion."""

    def test_uniform_depth_returns_max(self):
        """If entire frame is same depth, should return MAX_DEPTH_M."""
        est = _make_estimator()
        raw = np.ones((100, 100), dtype=np.float32) * 5.0
        result = est._normalize_depth(raw)
        assert result.shape == (100, 100)
        assert np.allclose(result, est.MAX_DEPTH_M)

    def test_close_objects_have_small_distance(self):
        """High raw values (close objects in MiDaS) → small metric distance."""
        est = _make_estimator()
        raw = np.zeros((100, 100), dtype=np.float32)
        raw[50, 50] = 100.0  # Closest point
        result = est._normalize_depth(raw)
        # The closest point should have the smallest distance
        center_dist = result[50, 50]
        corner_dist = result[0, 0]
        assert center_dist < corner_dist

    def test_output_dtype_is_float32(self):
        est = _make_estimator()
        raw = np.random.rand(50, 50).astype(np.float32) * 10
        result = est._normalize_depth(raw)
        assert result.dtype == np.float32

    def test_output_clamped_to_range(self):
        est = _make_estimator()
        raw = np.random.rand(50, 50).astype(np.float32)
        result = est._normalize_depth(raw)
        assert result.min() >= 0.3
        assert result.max() <= est.MAX_DEPTH_M


# =============================================================================
# get_distance_at
# =============================================================================

class TestGetDistanceAt:
    """Test point-distance queries on a depth map."""

    def test_center_point(self):
        est = _make_estimator()
        depth = np.full((100, 100), 5.0, dtype=np.float32)
        dist = est.get_distance_at(depth, 50, 50)
        assert abs(dist - 5.0) < 0.01

    def test_corner_clamped(self):
        """Coordinates outside frame should be clamped."""
        est = _make_estimator()
        depth = np.full((100, 100), 3.0, dtype=np.float32)
        dist = est.get_distance_at(depth, 999, 999)
        assert abs(dist - 3.0) < 0.01

    def test_none_depth_returns_max(self):
        est = _make_estimator()
        dist = est.get_distance_at(None, 50, 50)
        assert dist == est.MAX_DEPTH_M

    def test_patch_uses_median(self):
        """Verify that a noisy patch still returns the median."""
        est = _make_estimator()
        depth = np.full((100, 100), 5.0, dtype=np.float32)
        # Add one outlier in the patch area
        depth[50, 50] = 100.0
        dist = est.get_distance_at(depth, 50, 50, patch_size=10)
        # Median should still be close to 5.0 since most values are 5.0
        assert abs(dist - 5.0) < 1.0


# =============================================================================
# get_direction
# =============================================================================

class TestGetDirection:
    """Test horizontal direction classification."""

    @pytest.mark.parametrize("x,expected", [
        (50, "left"),           # 50/640 = 0.078
        (200, "slightly left"), # 200/640 = 0.3125
        (320, "center"),        # 320/640 = 0.5
        (450, "slightly right"),# 450/640 = 0.703
        (600, "right"),         # 600/640 = 0.9375
    ])
    def test_direction_zones(self, x, expected):
        est = _make_estimator()
        assert est.get_direction(x, 640) == expected

    def test_boundary_left(self):
        est = _make_estimator()
        # x/w = 0.2 → should be "slightly left" (>= 0.2)
        assert est.get_direction(128, 640) == "slightly left"

    def test_boundary_right(self):
        est = _make_estimator()
        # x/w = 0.8 → should be "right" (>= 0.8)
        assert est.get_direction(512, 640) == "right"


# =============================================================================
# enrich_detections
# =============================================================================

class TestEnrichDetections:
    """Test that detections get distance + direction populated."""

    def test_enriches_distance_and_direction(self):
        est = _make_estimator()
        depth = np.full((480, 640), 2.5, dtype=np.float32)
        det = Detection(
            class_name="person", confidence=0.9,
            bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        )
        est.enrich_detections([det], depth, 640)
        assert det.distance_m is not None
        assert abs(det.distance_m - 2.5) < 0.5
        assert det.direction is not None

    def test_none_depth_skips(self):
        est = _make_estimator()
        det = Detection(
            class_name="car", confidence=0.8,
            bbox=(0, 0, 100, 100), center_x=50, center_y=50,
        )
        est.enrich_detections([det], None, 640)
        assert det.distance_m is None
        assert det.direction is None

    def test_multiple_detections(self):
        est = _make_estimator()
        depth = np.full((480, 640), 4.0, dtype=np.float32)
        dets = [
            Detection("person", 0.9, (100, 100, 200, 200), 150, 150),
            Detection("car", 0.8, (400, 100, 600, 300), 500, 200),
        ]
        est.enrich_detections(dets, depth, 640)
        for d in dets:
            assert d.distance_m is not None
            assert d.direction is not None
