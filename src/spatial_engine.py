"""
AIVA - Spatial Intelligence Engine
=====================================
Decision engine that fuses object detection + depth estimation into
actionable safety warnings and environmental awareness descriptions.

This is NOT simple object detection — it implements obstacle avoidance
logic, warning priority, and structured environment reporting.

All outputs are derived strictly from model inference. No creative
additions, no speculative interpretation (anti-hallucination per PRD).
"""

import time
from typing import Dict, List, Optional, Tuple

from src.object_detector import Detection, SAFETY_PRIORITY_CLASSES


# Dual-threshold obstacle avoidance system
# Tier 1: Early warning — caution zone
CAUTION_DISTANCE = 1.5
# Tier 2: Immediate stop — danger zone
DANGER_DISTANCE = 1.2

# Frame region thresholds (horizontal position → direction)
LEFT_BOUNDARY = 0.33
RIGHT_BOUNDARY = 0.66


# Warning cooldown between same-class warnings (seconds)
WARNING_COOLDOWN = 2.0


class Warning:
    """A spatial warning for the user."""

    def __init__(
        self,
        message: str,
        priority: int,
        detection: Detection,
        is_critical: bool = False,
        zone: str = "caution"
    ):
        self.message = message
        self.priority = priority  # Lower = more urgent
        self.detection = detection
        self.is_critical = is_critical
        self.zone = zone  # "caution" (< 1.5m) or "danger" (< 1.2m)
        self.timestamp = time.time()

    def __repr__(self) -> str:
        return f"Warning('{self.message}', priority={self.priority}, zone={self.zone})"


class SpatialEngine:
    """
    Spatial intelligence engine for obstacle avoidance and environment awareness.

    Processes object detections enriched with depth data to produce:
    1. Real-time obstacle warnings with directional guidance
    2. Environment summaries ("What's around me?")

    Warning Priority (lower = more urgent):
        0 — Moving vehicles (car, bus, truck, motorcycle)
        1 — Bicycles
        2 — Animals (dog, cat)
        3 — Persons
        4 — Static obstacles (bench, fire hydrant, chair...)
        5+ — Other objects

    Usage:
        engine = SpatialEngine()
        warnings = engine.check_obstacles(detections)
        for w in warnings:
            speak(w.message)

        summary = engine.get_surroundings(detections)
        speak(summary)
    """

    # Max objects in surroundings description
    MAX_SURROUNDINGS = 3

    def __init__(
        self,
        caution_distance: float = CAUTION_DISTANCE,
        danger_distance: float = DANGER_DISTANCE,
        warning_cooldown: float = WARNING_COOLDOWN
    ):
        """
        Initialize the spatial engine.

        Args:
            caution_distance: Tier 1 threshold — early warning (meters)
            danger_distance: Tier 2 threshold — immediate stop (meters)
            warning_cooldown: Minimum seconds between same-class warnings
        """
        self._caution_distance = caution_distance
        self._danger_distance = danger_distance
        self._warning_cooldown = warning_cooldown
        self._last_warning_time: Dict[str, float] = {}
        self._last_warnings: List[Warning] = []

    def check_obstacles(self, detections: List[Detection]) -> List[Warning]:
        """
        Check for obstacles using dual-threshold system.

        Tier 1 — Caution Zone (< 1.5m):
            Voice: "Obstacle ahead." with directional guidance.

        Tier 2 — Danger Zone (< 1.2m):
            Voice: "Stop." Immediate halt required.

        Args:
            detections: List of Detection objects with distance/direction populated

        Returns:
            List of Warning objects, sorted by priority (most urgent first)
        """
        warnings: List[Warning] = []
        current_time = time.time()

        for det in detections:
            # Skip if no distance data
            if det.distance_m is None:
                continue

            # Skip if outside caution zone entirely
            if det.distance_m >= self._caution_distance:
                continue

            # Check cooldown for this class
            last_time = self._last_warning_time.get(det.class_name, 0)
            if current_time - last_time < self._warning_cooldown:
                continue

            # Get safety priority
            priority = SAFETY_PRIORITY_CLASSES.get(det.class_name, 5)

            # Determine zone
            if det.distance_m < self._danger_distance:
                zone = "danger"
            else:
                zone = "caution"

            # Generate directional warning
            direction = det.direction or "center"
            message = self._build_obstacle_message(det, direction, zone)

            # Critical: danger zone OR vehicles OR very close
            is_critical = (
                zone == "danger"
                or priority <= 1
                or det.distance_m < 0.8
            )

            warning = Warning(
                message=message,
                priority=priority,
                detection=det,
                is_critical=is_critical,
                zone=zone
            )
            warnings.append(warning)

            # Update cooldown
            self._last_warning_time[det.class_name] = current_time

        # Sort by priority (most urgent first)
        warnings.sort(key=lambda w: (w.priority, w.detection.distance_m or 999))

        self._last_warnings = warnings
        return warnings

    def _build_obstacle_message(
        self, det: Detection, direction: str, zone: str = "caution"
    ) -> str:
        """
        Build a concise obstacle warning message.

        Args:
            det: The detected obstacle
            direction: Directional context
            zone: "caution" or "danger"

        Returns:
            Warning message string
        """
        class_name = det.class_name
        distance = det.distance_m

        # Format distance
        if distance is not None:
            dist_str = f"{distance:.1f} meters"
        else:
            dist_str = "nearby"

        # Danger zone: immediate stop regardless of direction
        if zone == "danger":
            if direction in ("left",):
                return f"Stop! {class_name} {dist_str} to your left."
            elif direction in ("right",):
                return f"Stop! {class_name} {dist_str} to your right."
            else:
                return f"Stop! {class_name} {dist_str} ahead."

        # Caution zone: directional guidance
        if direction in ("center", "slightly left", "slightly right"):
            guidance = f"Caution, {class_name} {dist_str} ahead."
        elif direction in ("left",):
            guidance = f"{class_name} {dist_str} to your left. Move slightly right."
        elif direction in ("right",):
            guidance = f"{class_name} {dist_str} to your right. Move slightly left."
        else:
            guidance = f"{class_name} {dist_str} ahead."

        return guidance

    def get_surroundings(self, detections: List[Detection]) -> str:
        """
        Generate an environment awareness description.

        Responds to "What's around me?" by listing the top 3 nearest objects,
        sorted by distance. No creative additions.

        Args:
            detections: List of Detection objects with distance populated

        Returns:
            Structured description string
        """
        if not detections:
            return "I don't detect any objects around you right now."

        # Filter to detections with distance data
        with_distance = [d for d in detections if d.distance_m is not None]

        if not with_distance:
            # Fallback: describe what we see without distance
            names = list(set(d.class_name for d in detections[:self.MAX_SURROUNDINGS]))
            items = ", ".join(names)
            return f"I can see: {items}. Distance information is not available."

        # Sort by distance (nearest first)
        sorted_dets = sorted(with_distance, key=lambda d: d.distance_m)

        # Take top N
        top = sorted_dets[:self.MAX_SURROUNDINGS]

        # Build description
        parts = []
        for det in top:
            direction = det.direction or "ahead"
            if direction == "center":
                direction = "ahead"
            elif direction == "slightly left":
                direction = "slightly to your left"
            elif direction == "slightly right":
                direction = "slightly to your right"
            elif direction == "left":
                direction = "to your left"
            elif direction == "right":
                direction = "to your right"

            parts.append(
                f"A {det.class_name} {det.distance_m:.1f} meters {direction}"
            )

        # Join into natural sentence
        if len(parts) == 1:
            return f"There is {parts[0].lower()}."
        elif len(parts) == 2:
            return f"There is {parts[0].lower()}. {parts[1]}."
        else:
            result = f"There is {parts[0].lower()}. {parts[1]}. {parts[2]}."
            return result

    def get_danger_summary(self, detections: List[Detection]) -> Optional[str]:
        """
        Quick check: is there immediate danger?

        Returns a short urgent message if something dangerous is very close,
        or None if no immediate threat.

        Args:
            detections: List of Detection objects

        Returns:
            Urgent warning string or None
        """
        for det in detections:
            if det.distance_m is None:
                continue

            priority = SAFETY_PRIORITY_CLASSES.get(det.class_name, 5)

            # Vehicle within 2m
            if priority == 0 and det.distance_m < 2.0:
                return f"Warning! {det.class_name} approaching, {det.distance_m:.1f} meters!"

            # Any object within 0.5m
            if det.distance_m < 0.5:
                return f"Stop! {det.class_name} very close, {det.distance_m:.1f} meters!"

        return None

    @property
    def last_warnings(self) -> List[Warning]:
        """Most recent obstacle warnings."""
        return self._last_warnings


# Quick test with mock data when run directly
if __name__ == "__main__":
    print("SpatialEngine Module Test")
    print("=" * 40)

    engine = SpatialEngine()

    # Create mock detections
    mock_detections = [
        Detection(
            class_name="person",
            confidence=0.85,
            bbox=(100, 100, 200, 300),
            center_x=150,
            center_y=200,
            distance_m=2.0,
            direction="center"
        ),
        Detection(
            class_name="car",
            confidence=0.92,
            bbox=(400, 150, 600, 350),
            center_x=500,
            center_y=250,
            distance_m=5.0,
            direction="right"
        ),
        Detection(
            class_name="bench",
            confidence=0.71,
            bbox=(50, 300, 180, 400),
            center_x=115,
            center_y=350,
            distance_m=1.2,
            direction="left"
        ),
    ]

    print("\n--- Obstacle Check ---")
    warnings = engine.check_obstacles(mock_detections)
    for w in warnings:
        print(f"  [{w.priority}] {'🚨' if w.is_critical else '⚠️'} {w.message}")

    print("\n--- Surroundings ---")
    summary = engine.get_surroundings(mock_detections)
    print(f"  {summary}")

    print("\n--- Danger Summary ---")
    danger = engine.get_danger_summary(mock_detections)
    print(f"  {danger or 'No immediate danger'}")

    # Test with close vehicle
    print("\n--- Close Vehicle Test ---")
    close_car = Detection(
        class_name="car",
        confidence=0.95,
        bbox=(200, 100, 500, 400),
        center_x=350,
        center_y=250,
        distance_m=1.0,
        direction="center"
    )
    warnings = engine.check_obstacles([close_car])
    for w in warnings:
        print(f"  [{w.priority}] {'🚨' if w.is_critical else '⚠️'} {w.message}")

    danger = engine.get_danger_summary([close_car])
    print(f"  Danger: {danger}")
