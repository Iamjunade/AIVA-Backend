"""
Tests for AIVA Spatial Engine — Dual-Threshold System
"""
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.object_detector import Detection
from src.spatial_engine import SpatialEngine, CAUTION_DISTANCE, DANGER_DISTANCE


def test_danger_zone_center_stop():
    """Object dead center < 1.2m (danger zone) should generate 'Stop!' warning."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="bench", confidence=0.8,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=0.9, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1, "Should generate at least one warning"
    assert warnings[0].zone == "danger", f"Expected danger zone, got {warnings[0].zone}"
    assert "stop" in warnings[0].message.lower(), f"Expected 'Stop', got: {warnings[0].message}"
    assert warnings[0].is_critical is True, "Danger zone should be critical"
    print("  OK: Danger zone center -> Stop!")


def test_caution_zone_center_ahead():
    """Object center between 1.2m and 1.5m should generate 'Caution' warning."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="bench", confidence=0.8,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=1.35, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1, "Should generate at least one warning"
    assert warnings[0].zone == "caution", f"Expected caution zone, got {warnings[0].zone}"
    assert "caution" in warnings[0].message.lower(), f"Expected 'Caution', got: {warnings[0].message}"
    print("  OK: Caution zone center -> Caution ahead")


def test_danger_zone_left():
    """Object on left < 1.2m should say 'Stop!' with direction."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="pole", confidence=0.75,
        bbox=(50, 100, 120, 300), center_x=85, center_y=200,
        distance_m=1.0, direction="left"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1
    assert warnings[0].zone == "danger"
    assert "stop" in warnings[0].message.lower()
    assert "left" in warnings[0].message.lower()
    print("  OK: Danger zone left -> Stop! ... to your left")


def test_caution_zone_left_move_right():
    """Object on left between 1.2-1.5m should suggest 'move slightly right'."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="pole", confidence=0.75,
        bbox=(50, 100, 120, 300), center_x=85, center_y=200,
        distance_m=1.4, direction="left"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1
    assert warnings[0].zone == "caution"
    assert "right" in warnings[0].message.lower()
    print("  OK: Caution zone left -> Move right")


def test_caution_zone_right_move_left():
    """Object on the right in caution zone should suggest 'move slightly left'."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="dog", confidence=0.82,
        bbox=(500, 100, 600, 300), center_x=550, center_y=200,
        distance_m=1.35, direction="right"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1
    assert "left" in warnings[0].message.lower()
    assert warnings[0].zone == "caution"
    print("  OK: Caution zone right -> Move left")


def test_no_warning_far_objects():
    """Objects >=1.5m should not generate warnings."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="person", confidence=0.9,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=3.0, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) == 0, f"Should not warn for objects at 3m, got {len(warnings)}"
    print("  OK: Far objects -> No warning")


def test_boundary_1_5m_no_warning():
    """Objects at exactly 1.5m should NOT generate warnings (>= threshold)."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="person", confidence=0.9,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=1.5, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) == 0, f"Object at exactly 1.5m should not trigger warning"
    print("  OK: At 1.5m boundary -> No warning")


def test_boundary_1_49m_caution():
    """Objects at 1.49m should trigger caution zone warning."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="person", confidence=0.9,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=1.49, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1, "1.49m should trigger caution"
    assert warnings[0].zone == "caution"
    print("  OK: At 1.49m -> Caution zone")


def test_boundary_1_2m_danger():
    """Objects at < 1.2m should trigger danger zone."""
    engine = SpatialEngine(warning_cooldown=0)
    det = Detection(
        class_name="person", confidence=0.9,
        bbox=(200, 100, 400, 300), center_x=300, center_y=200,
        distance_m=1.19, direction="center"
    )
    warnings = engine.check_obstacles([det])
    assert len(warnings) >= 1, "1.19m should trigger danger"
    assert warnings[0].zone == "danger"
    assert warnings[0].is_critical is True
    print("  OK: At 1.19m -> Danger zone (critical)")


def test_warning_priority_vehicle_first():
    """Vehicle warnings should come before person warnings."""
    engine = SpatialEngine(warning_cooldown=0)
    dets = [
        Detection(
            class_name="person", confidence=0.85,
            bbox=(200, 100, 300, 300), center_x=250, center_y=200,
            distance_m=1.0, direction="center"
        ),
        Detection(
            class_name="car", confidence=0.91,
            bbox=(400, 100, 600, 350), center_x=500, center_y=200,
            distance_m=1.3, direction="right"
        ),
    ]
    warnings = engine.check_obstacles(dets)
    assert len(warnings) == 2
    assert warnings[0].detection.class_name == "car", "Car should have higher priority"
    print("  OK: Vehicle priority > Person priority")


def test_surroundings_top3_sorted():
    """Surroundings should list top 3 nearest objects, sorted by distance."""
    engine = SpatialEngine()
    dets = [
        Detection(class_name="person", confidence=0.8, bbox=(0,0,1,1),
                  center_x=300, center_y=200, distance_m=5.0, direction="center"),
        Detection(class_name="bench", confidence=0.7, bbox=(0,0,1,1),
                  center_x=100, center_y=200, distance_m=2.0, direction="left"),
        Detection(class_name="car", confidence=0.9, bbox=(0,0,1,1),
                  center_x=500, center_y=200, distance_m=8.0, direction="right"),
        Detection(class_name="dog", confidence=0.75, bbox=(0,0,1,1),
                  center_x=300, center_y=300, distance_m=3.0, direction="center"),
    ]
    summary = engine.get_surroundings(dets)
    assert "bench" in summary.lower(), f"Nearest (bench) should be mentioned: {summary}"
    assert "dog" in summary.lower(), f"2nd nearest (dog) should be mentioned: {summary}"
    assert "person" in summary.lower(), f"3rd nearest (person) should be mentioned: {summary}"
    assert "car" not in summary.lower(), f"4th object (car) should NOT be in top 3: {summary}"
    print(f"  OK: Surroundings: {summary}")


def test_surroundings_empty():
    """No detections should return appropriate message."""
    engine = SpatialEngine()
    summary = engine.get_surroundings([])
    assert "don't detect" in summary.lower() or "no" in summary.lower()
    print("  OK: Empty surroundings handled")


def test_danger_vehicle_close():
    """Vehicle within 2m should trigger danger summary."""
    engine = SpatialEngine()
    det = Detection(
        class_name="car", confidence=0.95,
        bbox=(200, 100, 500, 400), center_x=350, center_y=250,
        distance_m=1.5, direction="center"
    )
    danger = engine.get_danger_summary([det])
    assert danger is not None, "Should detect danger"
    assert "car" in danger.lower()
    print(f"  OK: Danger: {danger}")


def test_threshold_constants():
    """Verify threshold constants are correct."""
    assert CAUTION_DISTANCE == 1.5, f"CAUTION_DISTANCE should be 1.5, got {CAUTION_DISTANCE}"
    assert DANGER_DISTANCE == 1.2, f"DANGER_DISTANCE should be 1.2, got {DANGER_DISTANCE}"
    assert CAUTION_DISTANCE > DANGER_DISTANCE, "Caution must be > Danger distance"
    print("  OK: Threshold constants correct (1.5m caution, 1.2m danger)")


if __name__ == "__main__":
    print("=== Spatial Engine Tests (Dual-Threshold) ===\n")
    test_threshold_constants()
    test_danger_zone_center_stop()
    test_caution_zone_center_ahead()
    test_danger_zone_left()
    test_caution_zone_left_move_right()
    test_caution_zone_right_move_left()
    test_no_warning_far_objects()
    test_boundary_1_5m_no_warning()
    test_boundary_1_49m_caution()
    test_boundary_1_2m_danger()
    test_warning_priority_vehicle_first()
    test_surroundings_top3_sorted()
    test_surroundings_empty()
    test_danger_vehicle_close()
    print("\nAll 14 spatial engine tests passed!")
