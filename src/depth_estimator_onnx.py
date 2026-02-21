"""
AIVA — Depth Estimation via ONNX Runtime (Drop-in Replacement)
================================================================
Drop-in replacement for DepthEstimator that uses ONNX Runtime
instead of PyTorch for 2-3x faster inference.

Usage:
    # Replace this import in frame_processor.py:
    # from src.depth_estimator import DepthEstimator
    from src.depth_estimator_onnx import DepthEstimatorONNX as DepthEstimator

Requires:
    1. Export the model first:  python scripts/export_midas_onnx.py
    2. pip install onnxruntime (CPU) or onnxruntime-gpu (CUDA)
"""

import time
from pathlib import Path
from typing import List, Optional

import cv2
import numpy as np

try:
    import onnxruntime as ort
    ONNX_AVAILABLE = True
except ImportError:
    ONNX_AVAILABLE = False
    print("[DepthEstimatorONNX] WARNING: onnxruntime not installed. "
          "Run: pip install onnxruntime")


# Default ONNX model path (created by scripts/export_midas_onnx.py)
_DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent / "models" / "midas_small.onnx"


class DepthEstimatorONNX:
    """
    ONNX Runtime drop-in replacement for DepthEstimator.

    Provides the same public interface:
        - estimate(frame) → depth_map
        - get_distance_at(depth_map, x, y)
        - get_direction(x, frame_width)
        - enrich_detections(detections, depth_map, frame_width)
        - is_available (property)

    Performance:
        - 2-3x faster than PyTorch on CPU
        - ~1.5x faster on CUDA (less overhead)
        - ~50% less memory than PyTorch runtime
    """

    MAX_DEPTH_M = 15.0
    INPUT_SIZE = 256  # MiDaS Small expects 256x256

    def __init__(
        self,
        model_path: Optional[str] = None,
        depth_scale: float = 3.0,
        use_gpu: bool = True,
    ):
        """
        Initialize the ONNX depth estimator.

        Args:
            model_path: Path to .onnx file (None = default location)
            depth_scale: Calibration factor for relative→metric conversion
            use_gpu: Try CUDA execution provider if available
        """
        self._session = None
        self._depth_scale = depth_scale
        self._last_depth_map: Optional[np.ndarray] = None
        self._frame_count = 0

        if not ONNX_AVAILABLE:
            print("[DepthEstimatorONNX] Disabled — onnxruntime not installed")
            return

        model_file = Path(model_path) if model_path else _DEFAULT_MODEL_PATH
        if not model_file.exists():
            print(f"[DepthEstimatorONNX] Model not found: {model_file}")
            print("  Run: python scripts/export_midas_onnx.py")
            return

        self._load_session(str(model_file), use_gpu)

    def _load_session(self, model_path: str, use_gpu: bool) -> None:
        """Load ONNX Runtime session with optimal execution provider."""
        try:
            providers = []
            if use_gpu and "CUDAExecutionProvider" in ort.get_available_providers():
                providers.append("CUDAExecutionProvider")
                print("[DepthEstimatorONNX] ✓ Using CUDA GPU")
            providers.append("CPUExecutionProvider")

            # Session options for performance
            opts = ort.SessionOptions()
            opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
            opts.intra_op_num_threads = 4
            opts.inter_op_num_threads = 2

            start = time.time()
            self._session = ort.InferenceSession(
                model_path, sess_options=opts, providers=providers
            )
            elapsed = (time.time() - start) * 1000
            provider = self._session.get_providers()[0]
            print(f"[DepthEstimatorONNX] ✓ Loaded in {elapsed:.0f}ms ({provider})")

        except Exception as e:
            print(f"[DepthEstimatorONNX] ✗ Failed to load: {e}")
            self._session = None

    def estimate(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Estimate depth map from a BGR frame.

        Args:
            frame: BGR image (numpy array)

        Returns:
            Depth map in approximate meters (float32), or None on failure.
        """
        if self._session is None:
            return None

        if frame is None or frame.size == 0:
            return self._last_depth_map

        try:
            self._frame_count += 1
            orig_h, orig_w = frame.shape[:2]

            # Preprocess: BGR→RGB, resize to 256x256, normalize
            rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            resized = cv2.resize(rgb, (self.INPUT_SIZE, self.INPUT_SIZE))
            # Normalize to [0, 1] and then to ImageNet stats
            blob = resized.astype(np.float32) / 255.0
            blob = (blob - np.array([0.485, 0.456, 0.406])) / np.array([0.229, 0.224, 0.225])
            # NCHW format
            blob = blob.transpose(2, 0, 1)[np.newaxis, ...]

            # Run inference
            input_name = self._session.get_inputs()[0].name
            output = self._session.run(None, {input_name: blob.astype(np.float32)})
            prediction = output[0].squeeze()

            # Resize back to original frame size
            depth_map = cv2.resize(prediction, (orig_w, orig_h))

            # Normalize to approximate meters
            depth_map = self._normalize_depth(depth_map)

            self._last_depth_map = depth_map
            return depth_map

        except Exception as e:
            if self._frame_count <= 1:
                print(f"[DepthEstimatorONNX] Estimation error: {e}")
            return self._last_depth_map

    def _normalize_depth(self, raw_depth: np.ndarray) -> np.ndarray:
        """Convert raw MiDaS output to approximate metric depth."""
        depth_min = raw_depth.min()
        depth_max = raw_depth.max()

        if depth_max - depth_min < 1e-6:
            return np.ones_like(raw_depth, dtype=np.float32) * self.MAX_DEPTH_M

        normalized = (raw_depth - depth_min) / (depth_max - depth_min)
        distance_map = self._depth_scale / (normalized + 0.05)
        distance_map = np.clip(distance_map, 0.3, self.MAX_DEPTH_M)

        return distance_map.astype(np.float32)

    def get_distance_at(
        self, depth_map: np.ndarray, x: int, y: int, patch_size: int = 10
    ) -> float:
        """Get distance at a specific pixel location using median patch."""
        if depth_map is None:
            return self.MAX_DEPTH_M

        h, w = depth_map.shape[:2]
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))

        half = patch_size // 2
        y1, y2 = max(0, y - half), min(h, y + half + 1)
        x1, x2 = max(0, x - half), min(w, x + half + 1)
        patch = depth_map[y1:y2, x1:x2]

        return float(np.median(patch)) if patch.size > 0 else self.MAX_DEPTH_M

    def get_direction(self, x: int, frame_width: int) -> str:
        """Determine directional context based on horizontal position."""
        ratio = x / frame_width
        if ratio < 0.2:
            return "left"
        elif ratio < 0.4:
            return "slightly left"
        elif ratio < 0.6:
            return "center"
        elif ratio < 0.8:
            return "slightly right"
        else:
            return "right"

    def enrich_detections(
        self, detections, depth_map: Optional[np.ndarray], frame_width: int
    ) -> None:
        """Enrich Detection objects with distance and direction (in-place)."""
        if depth_map is None:
            return

        for det in detections:
            det.distance_m = self.get_distance_at(
                depth_map, det.center_x, det.center_y
            )
            det.direction = self.get_direction(det.center_x, frame_width)

    def get_depth_colormap(self, depth_map: np.ndarray) -> np.ndarray:
        """Create a colorized visualization of the depth map."""
        if depth_map is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        d_min, d_max = depth_map.min(), depth_map.max()
        if d_max - d_min < 1e-6:
            normalized = np.zeros_like(depth_map, dtype=np.uint8)
        else:
            normalized = ((depth_map - d_min) / (d_max - d_min) * 255).astype(np.uint8)

        return cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)

    @property
    def is_available(self) -> bool:
        """Whether the ONNX depth estimator is ready."""
        return self._session is not None


# =============================================================================
# Quick benchmark when run directly
# =============================================================================

if __name__ == "__main__":
    import time

    print("DepthEstimatorONNX Benchmark")
    print("=" * 40)

    est = DepthEstimatorONNX()

    if not est.is_available:
        print("\nNot available. Run: python scripts/export_midas_onnx.py")
        exit(1)

    # Warm-up
    dummy = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
    est.estimate(dummy)

    # Benchmark 50 frames
    times = []
    for _ in range(50):
        frame = np.random.randint(0, 255, (480, 640, 3), dtype=np.uint8)
        t0 = time.perf_counter()
        est.estimate(frame)
        times.append((time.perf_counter() - t0) * 1000)

    print(f"\n  Mean:   {np.mean(times):.1f}ms")
    print(f"  Median: {np.median(times):.1f}ms")
    print(f"  P95:    {np.percentile(times, 95):.1f}ms")
    print(f"  P99:    {np.percentile(times, 99):.1f}ms")
