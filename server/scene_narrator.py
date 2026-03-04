"""
AIVA Server — Proactive Scene Narrator
=========================================
Background AI engine that automatically detects and narrates significant
scene changes — so AIVA speaks up when something important happens
without the user needing to ask.

Architecture:
    1. Receives detection snapshots from the frame processor after each frame
    2. Computes a semantic diff between current and previous scene state
    3. If the diff exceeds a significance threshold → triggers Gemini narration
    4. Pushes the narration to the connected client as a SpeechResponse

Throttling:
    - Minimum cooldown between narrations (default: 8s)
    - Max narrations per minute cap (default: 4)
    - Deduplication of recent narrations

Examples of proactive narrations:
    - "A car just appeared on your right."
    - "You've entered a room with a table and chairs."
    - "The person ahead of you has moved away."
"""

import asyncio
import logging
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

logger = logging.getLogger("aiva.narrator")


# =============================================================================
# SCENE STATE
# =============================================================================

@dataclass(frozen=True)
class SceneObject:
    """A detected object in the scene with spatial context."""
    class_name: str
    direction: Optional[str] = None      # "left", "center", "right"
    distance_m: Optional[float] = None   # approximate meters

    @property
    def key(self) -> str:
        """Unique key for this object (class + direction bucket)."""
        return f"{self.class_name}@{self.direction or 'unknown'}"


@dataclass
class SceneState:
    """Snapshot of the visual scene at a point in time."""
    objects: List[SceneObject] = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def object_set(self) -> Set[str]:
        """Set of object class names present in the scene."""
        return {obj.class_name for obj in self.objects}

    @property
    def object_keys(self) -> Set[str]:
        """Set of object keys (class+direction) present in the scene."""
        return {obj.key for obj in self.objects}

    def count_by_class(self) -> Dict[str, int]:
        """Count of each object class in the scene."""
        counts: Dict[str, int] = {}
        for obj in self.objects:
            counts[obj.class_name] = counts.get(obj.class_name, 0) + 1
        return counts


# =============================================================================
# SCENE DIFF
# =============================================================================

@dataclass
class SceneDiff:
    """Semantic diff between two scene states."""
    appeared: List[SceneObject] = field(default_factory=list)   # New objects
    disappeared: List[str] = field(default_factory=list)         # Class names gone
    approaching: List[SceneObject] = field(default_factory=list) # Objects getting closer
    receding: List[SceneObject] = field(default_factory=list)    # Objects moving away

    @property
    def total_changes(self) -> int:
        return len(self.appeared) + len(self.disappeared) + \
               len(self.approaching) + len(self.receding)

    @property
    def is_significant(self) -> bool:
        """Whether this diff represents a meaningful scene change."""
        # Any safety-critical object appearing is always significant
        safety_classes = {"car", "truck", "bus", "motorcycle", "bicycle", "dog"}
        for obj in self.appeared:
            if obj.class_name in safety_classes:
                return True
        # Any approaching object is significant
        if self.approaching:
            return True
        # Multiple changes = scene shift
        return self.total_changes >= 2

    def to_description(self) -> str:
        """
        Build a structured description of the diff for Gemini.
        This is NOT the narration — it's the context fed to Gemini.
        """
        parts = []
        if self.appeared:
            names = [f"{o.class_name} ({o.direction or 'ahead'})" for o in self.appeared]
            parts.append(f"NEW objects appeared: {', '.join(names)}")
        if self.disappeared:
            parts.append(f"Objects LEFT the scene: {', '.join(self.disappeared)}")
        if self.approaching:
            details = [
                f"{o.class_name} ({o.distance_m:.1f}m {o.direction or 'ahead'})"
                for o in self.approaching if o.distance_m is not None
            ]
            if details:
                parts.append(f"Objects APPROACHING: {', '.join(details)}")
        if self.receding:
            details = [
                f"{o.class_name} ({o.distance_m:.1f}m {o.direction or 'ahead'})"
                for o in self.receding if o.distance_m is not None
            ]
            if details:
                parts.append(f"Objects MOVING AWAY: {', '.join(details)}")
        return ". ".join(parts) if parts else ""


def compute_scene_diff(
    prev: SceneState,
    curr: SceneState,
    distance_threshold: float = 1.0,
) -> SceneDiff:
    """
    Compute the semantic diff between two scene states.

    Args:
        prev: Previous scene state
        curr: Current scene state
        distance_threshold: Minimum distance change (meters) to count as approaching/receding

    Returns:
        SceneDiff describing what changed
    """
    diff = SceneDiff()

    prev_classes = prev.count_by_class()
    curr_classes = curr.count_by_class()
    all_classes = set(prev_classes.keys()) | set(curr_classes.keys())

    # Build lookup: class_name -> list of objects with distances
    prev_lookup: Dict[str, List[SceneObject]] = {}
    curr_lookup: Dict[str, List[SceneObject]] = {}
    for obj in prev.objects:
        prev_lookup.setdefault(obj.class_name, []).append(obj)
    for obj in curr.objects:
        curr_lookup.setdefault(obj.class_name, []).append(obj)

    for cls in all_classes:
        prev_count = prev_classes.get(cls, 0)
        curr_count = curr_classes.get(cls, 0)

        if curr_count > prev_count:
            # New instances appeared
            new_objs = curr_lookup.get(cls, [])
            # Report the newest ones (those not matching old directions)
            for obj in new_objs[:curr_count - prev_count]:
                diff.appeared.append(obj)

        elif curr_count < prev_count:
            # Some instances disappeared
            diff.disappeared.append(cls)

        # Check distance changes for objects that persist
        if prev_count > 0 and curr_count > 0:
            prev_objs = prev_lookup.get(cls, [])
            curr_objs = curr_lookup.get(cls, [])

            # Compare closest instance of each class
            prev_closest = min(
                (o for o in prev_objs if o.distance_m is not None),
                key=lambda o: o.distance_m,
                default=None,
            )
            curr_closest = min(
                (o for o in curr_objs if o.distance_m is not None),
                key=lambda o: o.distance_m,
                default=None,
            )

            if prev_closest and curr_closest and \
               prev_closest.distance_m is not None and curr_closest.distance_m is not None:
                delta = prev_closest.distance_m - curr_closest.distance_m
                if delta > distance_threshold:
                    diff.approaching.append(curr_closest)
                elif delta < -distance_threshold:
                    diff.receding.append(curr_closest)

    return diff


# =============================================================================
# SCENE NARRATOR
# =============================================================================

# Narration prompt template for Gemini
NARRATION_PROMPT = (
    "You are AIVA, an AI assistant for a blind user. "
    "The scene has just changed. Here is what happened:\n\n"
    "{diff_description}\n\n"
    "Generate a single SHORT sentence (max 15 words) to inform the user "
    "about the most important change. Be natural and conversational. "
    "Prioritize safety-relevant changes (vehicles, obstacles). "
    "Do NOT use markdown. Do NOT say 'I detected' or 'I noticed'. "
    "Speak directly as if you're their companion.\n\n"
    "Examples of good responses:\n"
    "- 'A car just appeared on your right.'\n"
    "- 'There's now a dog near you on the left.'\n"
    "- 'The path ahead is clear now.'\n"
    "- 'You're entering a more crowded area.'"
)


class SceneNarrator:
    """
    Proactive scene narration engine.

    Runs as a background processor that:
    1. Tracks scene state from detection results
    2. Detects significant changes via semantic diff
    3. Generates natural narrations via Gemini
    4. Pushes them to the client as SpeechResponse

    Thread-safe: designed to receive updates from the async frame
    processing pipeline and push results back asynchronously.
    """

    def __init__(
        self,
        send_callback,
        cooldown_sec: float = 8.0,
        max_per_minute: int = 4,
        min_changes: int = 2,
        distance_threshold: float = 1.0,
    ):
        """
        Initialize the scene narrator.

        Args:
            send_callback: Async callable that accepts a narration string
                          and sends it to the client (as SpeechResponse)
            cooldown_sec: Minimum seconds between narrations
            max_per_minute: Maximum narrations per minute
            min_changes: Minimum total changes to trigger (unless safety-critical)
            distance_threshold: Minimum distance change to count
        """
        self._send_callback = send_callback
        self._cooldown_sec = cooldown_sec
        self._max_per_minute = max_per_minute
        self._min_changes = min_changes
        self._distance_threshold = distance_threshold

        # State
        self._prev_scene: Optional[SceneState] = None
        self._lock = threading.Lock()
        self._running = True

        # Throttle tracking
        self._last_narration_time: float = 0.0
        self._narration_timestamps: deque = deque(maxlen=max_per_minute + 5)
        self._recent_narrations: deque = deque(maxlen=10)  # Dedup buffer

        # Gemini model (lazy init)
        self._model = None
        self._initialize_gemini()

        # Event loop reference for async pushes from sync context
        self._loop: Optional[asyncio.AbstractEventLoop] = None

        logger.info(
            f"[SceneNarrator] Initialized "
            f"(cooldown={cooldown_sec}s, max/min={max_per_minute}, "
            f"min_changes={min_changes})"
        )

    def _initialize_gemini(self):
        """Initialize Gemini model for narration generation."""
        try:
            import google.generativeai as genai
            import os
            from dotenv import load_dotenv
            from pathlib import Path

            env_path = Path(__file__).resolve().parent.parent / ".env"
            if env_path.exists():
                load_dotenv(env_path)

            api_key = os.environ.get("GOOGLE_API_KEY")
            if not api_key or api_key == "your_api_key_here":
                logger.warning("[SceneNarrator] No Gemini API key — narration disabled")
                return

            genai.configure(api_key=api_key)
            self._model = genai.GenerativeModel(model_name="gemini-2.0-flash")
            logger.info("[SceneNarrator] ✓ Gemini model ready for narration")
        except Exception as e:
            logger.error(f"[SceneNarrator] ✗ Gemini init failed: {e}")

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        """Set the asyncio event loop for async pushes."""
        self._loop = loop

    def stop(self):
        """Stop the narrator."""
        self._running = False
        logger.info("[SceneNarrator] Stopped")

    # =========================================================================
    # PUBLIC INTERFACE — called from frame processing pipeline
    # =========================================================================

    def update_scene(self, detections: List[Dict]) -> None:
        """
        Feed new detection results into the narrator.

        Called after each frame is processed. This method is fast and
        non-blocking — heavy work (Gemini calls) happens in background.

        Args:
            detections: List of detection dicts from FrameResponse
                       Each dict has: class, confidence, distance_m, direction, bbox
        """
        if not self._running:
            return

        # Build current scene state from detections
        objects = []
        for det in detections:
            obj = SceneObject(
                class_name=det.get("class", "unknown"),
                direction=det.get("direction"),
                distance_m=det.get("distance_m"),
            )
            objects.append(obj)

        curr_scene = SceneState(objects=objects)

        with self._lock:
            prev_scene = self._prev_scene
            self._prev_scene = curr_scene

        # Skip if no previous scene (first frame)
        if prev_scene is None:
            return

        # Compute diff
        diff = compute_scene_diff(
            prev_scene, curr_scene,
            distance_threshold=self._distance_threshold,
        )

        # Check significance
        if not diff.is_significant and diff.total_changes < self._min_changes:
            return

        # Check throttle
        if not self._can_narrate():
            return

        # Generate and send narration (in background thread to avoid blocking)
        diff_desc = diff.to_description()
        if diff_desc:
            threading.Thread(
                target=self._generate_and_send,
                args=(diff_desc,),
                daemon=True,
            ).start()

    # =========================================================================
    # INTERNAL — throttle, generate, send
    # =========================================================================

    def _can_narrate(self) -> bool:
        """Check if we're allowed to narrate (cooldown + rate limit)."""
        now = time.time()

        # Cooldown check
        if now - self._last_narration_time < self._cooldown_sec:
            return False

        # Rate limit: count narrations in the last 60 seconds
        cutoff = now - 60.0
        recent_count = sum(1 for t in self._narration_timestamps if t > cutoff)
        if recent_count >= self._max_per_minute:
            return False

        return True

    def _generate_and_send(self, diff_description: str) -> None:
        """
        Generate narration via Gemini and push to client.
        Runs in a background thread.
        """
        try:
            narration = self._generate_narration(diff_description)
            if not narration:
                return

            # Deduplication: skip if we recently said something very similar
            if self._is_duplicate(narration):
                logger.debug(f"[SceneNarrator] Skipped duplicate: '{narration}'")
                return

            # Record timestamps
            now = time.time()
            self._last_narration_time = now
            self._narration_timestamps.append(now)
            self._recent_narrations.append(narration.lower().strip())

            logger.info(f"[SceneNarrator] Narrating: '{narration}'")

            # Push to client via async callback
            if self._loop and self._send_callback:
                asyncio.run_coroutine_threadsafe(
                    self._send_callback(narration),
                    self._loop,
                )

        except Exception as e:
            logger.error(f"[SceneNarrator] Narration error: {e}")

    def _generate_narration(self, diff_description: str) -> Optional[str]:
        """
        Use Gemini to generate a natural narration from the scene diff.

        Falls back to a template-based narration if Gemini is unavailable.
        """
        # Fallback if no Gemini
        if not self._model:
            return self._fallback_narration(diff_description)

        try:
            prompt = NARRATION_PROMPT.format(diff_description=diff_description)
            response = self._model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": 50,
                    "temperature": 0.3,
                },
            )
            text = response.text.strip()
            # Clean up Gemini output
            text = text.replace('"', '').replace("'", "").strip()
            # Ensure it's not too long for TTS
            if len(text) > 100:
                text = text[:97] + "..."
            return text if text else None

        except Exception as e:
            logger.warning(f"[SceneNarrator] Gemini narration failed: {e}")
            return self._fallback_narration(diff_description)

    def _fallback_narration(self, diff_description: str) -> Optional[str]:
        """
        Template-based fallback narration when Gemini is unavailable.
        Parses the diff_description string to generate a simple sentence.
        """
        if "NEW objects appeared" in diff_description:
            # Extract first new object
            try:
                start = diff_description.index("NEW objects appeared: ") + len("NEW objects appeared: ")
                end = diff_description.index("(", start)
                obj_name = diff_description[start:end].strip().rstrip(",")
                # Extract direction
                dir_start = end + 1
                dir_end = diff_description.index(")", dir_start)
                direction = diff_description[dir_start:dir_end]
                return f"There's a {obj_name} {direction}."
            except (ValueError, IndexError):
                pass

        if "Objects LEFT" in diff_description:
            try:
                start = diff_description.index("Objects LEFT the scene: ") + len("Objects LEFT the scene: ")
                end = diff_description.find(".", start)
                if end == -1:
                    end = len(diff_description)
                objects = diff_description[start:end].strip()
                return f"The {objects} is no longer there."
            except (ValueError, IndexError):
                pass

        if "APPROACHING" in diff_description:
            return "Something is getting closer to you."

        return None

    def _is_duplicate(self, narration: str) -> bool:
        """Check if this narration is too similar to recent ones."""
        narration_lower = narration.lower().strip()

        for recent in self._recent_narrations:
            # Simple similarity: check if the core content is the same
            if narration_lower == recent:
                return True
            # Check for high word overlap
            narr_words = set(narration_lower.split())
            recent_words = set(recent.split())
            if len(narr_words) > 2 and len(recent_words) > 2:
                overlap = len(narr_words & recent_words) / max(len(narr_words), len(recent_words))
                if overlap > 0.7:
                    return True

        return False
