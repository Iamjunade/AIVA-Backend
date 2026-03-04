"""
Tests for AIVA Proactive Scene Narrator
==========================================
Tests scene change detection, diff computation, throttling, 
deduplication, and fallback narration.
"""

import time
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from collections import deque

from server.scene_narrator import (
    SceneObject,
    SceneState,
    SceneDiff,
    SceneNarrator,
    compute_scene_diff,
)


# =============================================================================
# SCENE STATE
# =============================================================================

class TestSceneObject:
    """Test SceneObject dataclass."""

    def test_key_with_direction(self):
        obj = SceneObject(class_name="car", direction="left")
        assert obj.key == "car@left"

    def test_key_without_direction(self):
        obj = SceneObject(class_name="person", direction=None)
        assert obj.key == "person@unknown"


class TestSceneState:
    """Test SceneState dataclass."""

    def test_object_set(self):
        state = SceneState(objects=[
            SceneObject("car", "left"),
            SceneObject("person", "center"),
            SceneObject("car", "right"),
        ])
        assert state.object_set == {"car", "person"}

    def test_count_by_class(self):
        state = SceneState(objects=[
            SceneObject("car", "left"),
            SceneObject("person", "center"),
            SceneObject("car", "right"),
        ])
        counts = state.count_by_class()
        assert counts == {"car": 2, "person": 1}

    def test_empty_state(self):
        state = SceneState()
        assert state.object_set == set()
        assert state.count_by_class() == {}


# =============================================================================
# SCENE DIFF
# =============================================================================

class TestSceneDiff:
    """Test SceneDiff properties."""

    def test_total_changes(self):
        diff = SceneDiff(
            appeared=[SceneObject("car", "left")],
            disappeared=["person"],
        )
        assert diff.total_changes == 2

    def test_empty_diff(self):
        diff = SceneDiff()
        assert diff.total_changes == 0
        assert not diff.is_significant

    def test_safety_object_always_significant(self):
        diff = SceneDiff(appeared=[SceneObject("car", "right")])
        assert diff.is_significant

    def test_approaching_always_significant(self):
        diff = SceneDiff(approaching=[SceneObject("person", "center", 1.0)])
        assert diff.is_significant

    def test_single_non_safety_not_significant(self):
        diff = SceneDiff(appeared=[SceneObject("chair", "left")])
        assert not diff.is_significant  # Only 1 change, non-safety object

    def test_multiple_changes_significant(self):
        diff = SceneDiff(
            appeared=[SceneObject("chair", "left")],
            disappeared=["book"],
        )
        assert diff.is_significant  # 2+ changes = significant

    def test_to_description(self):
        diff = SceneDiff(
            appeared=[SceneObject("car", "right")],
            disappeared=["person"],
        )
        desc = diff.to_description()
        assert "NEW objects appeared" in desc
        assert "car" in desc
        assert "LEFT the scene" in desc
        assert "person" in desc


# =============================================================================
# COMPUTE SCENE DIFF
# =============================================================================

class TestComputeSceneDiff:
    """Test the core semantic diff algorithm."""

    def test_new_object_appears(self):
        prev = SceneState(objects=[SceneObject("person", "center", 2.0)])
        curr = SceneState(objects=[
            SceneObject("person", "center", 2.0),
            SceneObject("car", "right", 5.0),
        ])
        diff = compute_scene_diff(prev, curr)
        assert len(diff.appeared) == 1
        assert diff.appeared[0].class_name == "car"
        assert diff.disappeared == []

    def test_object_disappears(self):
        prev = SceneState(objects=[
            SceneObject("person", "center", 2.0),
            SceneObject("car", "right", 5.0),
        ])
        curr = SceneState(objects=[SceneObject("person", "center", 2.0)])
        diff = compute_scene_diff(prev, curr)
        assert "car" in diff.disappeared
        assert len(diff.appeared) == 0

    def test_object_approaching(self):
        prev = SceneState(objects=[SceneObject("person", "center", 5.0)])
        curr = SceneState(objects=[SceneObject("person", "center", 2.0)])
        diff = compute_scene_diff(prev, curr, distance_threshold=1.0)
        assert len(diff.approaching) == 1
        assert diff.approaching[0].distance_m == 2.0

    def test_object_receding(self):
        prev = SceneState(objects=[SceneObject("person", "center", 2.0)])
        curr = SceneState(objects=[SceneObject("person", "center", 5.0)])
        diff = compute_scene_diff(prev, curr, distance_threshold=1.0)
        assert len(diff.receding) == 1

    def test_no_change(self):
        state = SceneState(objects=[SceneObject("person", "center", 3.0)])
        diff = compute_scene_diff(state, state)
        assert diff.total_changes == 0

    def test_small_distance_change_ignored(self):
        """Changes below the distance_threshold should be ignored."""
        prev = SceneState(objects=[SceneObject("person", "center", 3.0)])
        curr = SceneState(objects=[SceneObject("person", "center", 2.5)])
        diff = compute_scene_diff(prev, curr, distance_threshold=1.0)
        assert len(diff.approaching) == 0
        assert len(diff.receding) == 0

    def test_empty_scenes(self):
        diff = compute_scene_diff(SceneState(), SceneState())
        assert diff.total_changes == 0

    def test_all_objects_appear(self):
        prev = SceneState()
        curr = SceneState(objects=[
            SceneObject("car", "left", 5.0),
            SceneObject("person", "center", 2.0),
        ])
        diff = compute_scene_diff(prev, curr)
        assert len(diff.appeared) == 2
        assert diff.disappeared == []

    def test_all_objects_disappear(self):
        prev = SceneState(objects=[
            SceneObject("car", "left", 5.0),
            SceneObject("person", "center", 2.0),
        ])
        curr = SceneState()
        diff = compute_scene_diff(prev, curr)
        assert len(diff.appeared) == 0
        assert len(diff.disappeared) == 2

    def test_no_distance_data(self):
        """Objects without distance data should not trigger approaching/receding."""
        prev = SceneState(objects=[SceneObject("person", "center", None)])
        curr = SceneState(objects=[SceneObject("person", "center", None)])
        diff = compute_scene_diff(prev, curr)
        assert len(diff.approaching) == 0
        assert len(diff.receding) == 0


# =============================================================================
# SCENE NARRATOR — THROTTLE LOGIC
# =============================================================================

class TestNarratorThrottling:
    """Test the narrator's throttling mechanisms."""

    def _make_narrator(self, **kwargs):
        """Create a narrator with Gemini disabled for unit tests."""
        defaults = {
            "send_callback": AsyncMock(),
            "cooldown_sec": 8.0,
            "max_per_minute": 4,
            "min_changes": 2,
            "distance_threshold": 1.0,
        }
        defaults.update(kwargs)
        with patch.object(SceneNarrator, '_initialize_gemini'):
            narrator = SceneNarrator(**defaults)
        narrator._model = None  # Ensure no Gemini calls
        return narrator

    def test_can_narrate_initially(self):
        narrator = self._make_narrator()
        assert narrator._can_narrate() is True

    def test_cooldown_blocks(self):
        narrator = self._make_narrator(cooldown_sec=10.0)
        narrator._last_narration_time = time.time()
        assert narrator._can_narrate() is False

    def test_cooldown_expires(self):
        narrator = self._make_narrator(cooldown_sec=0.1)
        narrator._last_narration_time = time.time() - 0.2
        assert narrator._can_narrate() is True

    def test_rate_limit_blocks(self):
        narrator = self._make_narrator(max_per_minute=2)
        now = time.time()
        narrator._narration_timestamps.extend([now - 10, now - 5])
        assert narrator._can_narrate() is False

    def test_rate_limit_passes_when_old_enough(self):
        narrator = self._make_narrator(max_per_minute=2)
        now = time.time()
        narrator._narration_timestamps.extend([now - 70, now - 65])
        assert narrator._can_narrate() is True


# =============================================================================
# SCENE NARRATOR — DEDUPLICATION
# =============================================================================

class TestNarratorDeduplication:
    """Test narration deduplication."""

    def _make_narrator(self):
        with patch.object(SceneNarrator, '_initialize_gemini'):
            narrator = SceneNarrator(send_callback=AsyncMock())
        narrator._model = None
        return narrator

    def test_exact_duplicate_detected(self):
        narrator = self._make_narrator()
        narrator._recent_narrations.append("a car just appeared on your right")
        assert narrator._is_duplicate("A car just appeared on your right") is True

    def test_high_overlap_detected(self):
        narrator = self._make_narrator()
        narrator._recent_narrations.append("a car appeared on your right side")
        assert narrator._is_duplicate("A car appeared on your right") is True

    def test_different_message_passes(self):
        narrator = self._make_narrator()
        narrator._recent_narrations.append("a car just appeared on your right")
        assert narrator._is_duplicate("The person has moved away") is False

    def test_empty_history_passes(self):
        narrator = self._make_narrator()
        assert narrator._is_duplicate("Any message here") is False


# =============================================================================
# SCENE NARRATOR — FALLBACK NARRATION
# =============================================================================

class TestFallbackNarration:
    """Test template-based fallback narration."""

    def _make_narrator(self):
        with patch.object(SceneNarrator, '_initialize_gemini'):
            narrator = SceneNarrator(send_callback=AsyncMock())
        narrator._model = None
        return narrator

    def test_appeared_fallback(self):
        narrator = self._make_narrator()
        desc = "NEW objects appeared: car (right)"
        result = narrator._fallback_narration(desc)
        assert result is not None
        assert "car" in result.lower()

    def test_disappeared_fallback(self):
        narrator = self._make_narrator()
        desc = "Objects LEFT the scene: person"
        result = narrator._fallback_narration(desc)
        assert result is not None
        assert "person" in result.lower()

    def test_approaching_fallback(self):
        narrator = self._make_narrator()
        desc = "Objects APPROACHING: car (2.0m center)"
        result = narrator._fallback_narration(desc)
        assert result is not None
        assert "closer" in result.lower()

    def test_empty_description_returns_none(self):
        narrator = self._make_narrator()
        result = narrator._fallback_narration("")
        assert result is None


# =============================================================================
# SCENE NARRATOR — UPDATE SCENE (Integration)
# =============================================================================

class TestUpdateScene:
    """Test the update_scene method end-to-end (with mocked Gemini)."""

    def _make_narrator(self, **kwargs):
        defaults = {
            "send_callback": AsyncMock(),
            "cooldown_sec": 0.0,
            "max_per_minute": 100,
            "min_changes": 1,
            "distance_threshold": 1.0,
        }
        defaults.update(kwargs)
        with patch.object(SceneNarrator, '_initialize_gemini'):
            narrator = SceneNarrator(**defaults)
        narrator._model = None
        return narrator

    def test_first_frame_no_narration(self):
        narrator = self._make_narrator()
        detections = [{"class": "person", "direction": "center", "distance_m": 3.0}]
        # First frame — should set state but not narrate
        narrator.update_scene(detections)
        assert narrator._prev_scene is not None
        # No narration thread should have been spawned

    def test_second_frame_with_change_triggers(self):
        narrator = self._make_narrator()
        # Frame 1
        narrator.update_scene([
            {"class": "person", "direction": "center", "distance_m": 3.0}
        ])
        # Frame 2: car appears (safety-critical, 1 change is enough)
        with patch.object(narrator, '_generate_and_send') as mock_gen:
            narrator.update_scene([
                {"class": "person", "direction": "center", "distance_m": 3.0},
                {"class": "car", "direction": "right", "distance_m": 5.0},
            ])
            mock_gen.assert_called_once()

    def test_no_change_no_trigger(self):
        narrator = self._make_narrator()
        detections = [{"class": "person", "direction": "center", "distance_m": 3.0}]
        narrator.update_scene(detections)
        with patch.object(narrator, '_generate_and_send') as mock_gen:
            narrator.update_scene(detections)
            mock_gen.assert_not_called()

    def test_stopped_narrator_does_nothing(self):
        narrator = self._make_narrator()
        narrator.stop()
        narrator.update_scene([{"class": "car", "direction": "right", "distance_m": 5.0}])
        assert narrator._prev_scene is None  # Never set because _running is False
