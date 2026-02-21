"""
AIVA - Depth Estimation Engine
================================
Monocular depth estimation using MiDaS v2.1 Small for approximate distance
measurement and directional context.

Converts relative depth maps into approximate metric distances using
a calibration factor. Provides per-object distance and direction info
when combined with object detection results.

Technology: MiDaS Small via torch.hub (~50MB model)
"""

from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    import torch
    TORCH_AVAILABLE = True
except ImportError:
    TORCH_AVAILABLE = False
    print("[DepthEstimator] WARNING: PyTorch not installed. Run: pip install torch torchvision")


class DepthEstimator:
    """
    Monocular depth estimation using MiDaS Small.

    Provides approximate distance estimation in meters from a single camera.
    Uses a calibration factor to convert relative depth to metric distances.

    IMPORTANT: Monocular depth is inherently approximate. Distances are
    estimates and may vary ±30% depending on scene conditions. The system
    communicates distances as approximate.

    Usage:
        estimator = DepthEstimator()
        depth_map = estimator.estimate(frame)
        distance = estimator.get_distance_at(depth_map, x=320, y=240)
    """

    # MiDaS model type — 'MiDaS_small' for speed on mobile/edge
    MODEL_TYPE = "MiDaS_small"

    # Calibration factor to convert relative depth to approximate meters.
    # This is a rough heuristic; ideally calibrated per-camera.
    # A typical webcam at ~60deg FOV: objects filling ~1/4 frame width
    # at 2m produce relative depth values around 0.3-0.5.
    DEPTH_SCALE_FACTOR = 3.0  # Multiplier for relative depth → meters

    # Maximum reasonable depth in meters (clamp outliers)
    MAX_DEPTH_M = 15.0

    def __init__(
        self,
        model_type: str = MODEL_TYPE,
        depth_scale: float = DEPTH_SCALE_FACTOR,
        device: Optional[str] = None
    ):
        """
        Initialize the depth estimator.

        Args:
            model_type: MiDaS model variant ('MiDaS_small', 'DPT_Large', etc.)
            depth_scale: Calibration factor for relative→metric conversion
            device: Force device ('cuda', 'cpu', or None for auto)
        """
        self._model = None
        self._transform = None
        self._device = None
        self._depth_scale = depth_scale
        self._last_depth_map: Optional[np.ndarray] = None
        self._frame_count = 0

        if not TORCH_AVAILABLE:
            print("[DepthEstimator] Depth estimation disabled — PyTorch not installed")
            return

        self._load_model(model_type, device)

    def _load_model(self, model_type: str, device: Optional[str]) -> None:
        """Load the MiDaS model from torch hub."""
        try:
            print(f"[DepthEstimator] Loading MiDaS model: {model_type}")

            # Determine device
            if device:
                self._device = torch.device(device)
            elif torch.cuda.is_available():
                self._device = torch.device("cuda")
                print("[DepthEstimator] ✓ Using CUDA GPU")
            else:
                self._device = torch.device("cpu")
                print("[DepthEstimator] Using CPU")

            # Load model
            self._model = torch.hub.load(
                "intel-isl/MiDaS", model_type,
                trust_repo=True
            )
            self._model.to(self._device)
            self._model.eval()

            # Load transform
            midas_transforms = torch.hub.load(
                "intel-isl/MiDaS", "transforms",
                trust_repo=True
            )

            if model_type == "MiDaS_small":
                self._transform = midas_transforms.small_transform
            elif "DPT" in model_type:
                self._transform = midas_transforms.dpt_transform
            else:
                self._transform = midas_transforms.default_transform

            print(f"[DepthEstimator] ✓ Model loaded on {self._device}")

        except Exception as e:
            print(f"[DepthEstimator] ✗ Failed to load model: {e}")
            self._model = None

    def estimate(self, frame: np.ndarray) -> Optional[np.ndarray]:
        """
        Estimate depth map from a BGR frame.

        Args:
            frame: BGR image from OpenCV (numpy array)

        Returns:
            Depth map as numpy array (float32), where higher values = closer.
            Normalized to approximate meters. Returns None on failure.
        """
        if self._model is None:
            return None

        if frame is None or frame.size == 0:
            return self._last_depth_map

        try:
            self._frame_count += 1

            # Convert BGR to RGB for MiDaS
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Apply MiDaS transform
            input_batch = self._transform(rgb_frame).to(self._device)

            # Run inference
            with torch.no_grad():
                prediction = self._model(input_batch)

                # Resize to original frame size
                prediction = torch.nn.functional.interpolate(
                    prediction.unsqueeze(1),
                    size=frame.shape[:2],
                    mode="bicubic",
                    align_corners=False
                ).squeeze()

            # Convert to numpy
            depth_map = prediction.cpu().numpy()

            # Normalize: MiDaS outputs inverse depth (higher = closer)
            # Convert to approximate meters
            depth_map = self._normalize_depth(depth_map)

            self._last_depth_map = depth_map
            return depth_map

        except Exception as e:
            if self._frame_count <= 1:
                print(f"[DepthEstimator] Estimation error: {e}")
            return self._last_depth_map

    def _normalize_depth(self, raw_depth: np.ndarray) -> np.ndarray:
        """
        Convert raw MiDaS output to approximate metric depth.

        MiDaS outputs inverse relative depth. We normalize and scale
        to produce approximate distances in meters.

        Args:
            raw_depth: Raw MiDaS output (inverse depth)

        Returns:
            Depth map in approximate meters
        """
        # Avoid division by zero
        depth_min = raw_depth.min()
        depth_max = raw_depth.max()

        if depth_max - depth_min < 1e-6:
            return np.ones_like(raw_depth) * self.MAX_DEPTH_M

        # Normalize to 0-1 range (inverted: 1 = closest, 0 = farthest)
        normalized = (raw_depth - depth_min) / (depth_max - depth_min)

        # Convert to distance: close objects have high values, far objects low
        # Invert so that higher normalized = closer = smaller distance
        # Apply scale factor for approximate meters
        # Add small epsilon to avoid division by zero
        distance_map = self._depth_scale / (normalized + 0.05)

        # Clamp to reasonable range
        distance_map = np.clip(distance_map, 0.3, self.MAX_DEPTH_M)

        return distance_map.astype(np.float32)

    def get_distance_at(
        self,
        depth_map: np.ndarray,
        x: int,
        y: int,
        patch_size: int = 10
    ) -> float:
        """
        Get distance at a specific pixel location.

        Uses a small patch around the point for stability (reduces noise).

        Args:
            depth_map: Depth map from estimate()
            x: X coordinate (pixels)
            y: Y coordinate (pixels)
            patch_size: Size of averaging patch

        Returns:
            Approximate distance in meters
        """
        if depth_map is None:
            return self.MAX_DEPTH_M

        h, w = depth_map.shape[:2]

        # Clamp coordinates
        x = max(0, min(x, w - 1))
        y = max(0, min(y, h - 1))

        # Extract patch
        half = patch_size // 2
        y1 = max(0, y - half)
        y2 = min(h, y + half + 1)
        x1 = max(0, x - half)
        x2 = min(w, x + half + 1)

        patch = depth_map[y1:y2, x1:x2]

        if patch.size == 0:
            return self.MAX_DEPTH_M

        # Use median for robustness against outliers
        return float(np.median(patch))

    def get_direction(self, x: int, frame_width: int) -> str:
        """
        Determine directional context based on horizontal position.

        Args:
            x: X coordinate in pixels
            frame_width: Total frame width

        Returns:
            Direction string: "left", "slightly left", "center",
            "slightly right", or "right"
        """
        relative_x = x / frame_width

        if relative_x < 0.2:
            return "left"
        elif relative_x < 0.4:
            return "slightly left"
        elif relative_x < 0.6:
            return "center"
        elif relative_x < 0.8:
            return "slightly right"
        else:
            return "right"

    def enrich_detections(
        self,
        detections,
        depth_map: Optional[np.ndarray],
        frame_width: int
    ) -> None:
        """
        Enrich Detection objects with distance and direction info.

        Modifies detections in-place.

        Args:
            detections: List of Detection objects from ObjectDetector
            depth_map: Depth map from estimate()
            frame_width: Width of the original frame
        """
        if depth_map is None:
            return

        for det in detections:
            # Get distance at object center
            det.distance_m = self.get_distance_at(
                depth_map, det.center_x, det.center_y
            )

            # Get refined direction
            det.direction = self.get_direction(det.center_x, frame_width)

    def get_depth_colormap(self, depth_map: np.ndarray) -> np.ndarray:
        """
        Create a colorized visualization of the depth map.

        Args:
            depth_map: Depth map from estimate()

        Returns:
            BGR colorized depth map for display
        """
        if depth_map is None:
            return np.zeros((480, 640, 3), dtype=np.uint8)

        # Normalize to 0-255 for visualization
        d_min, d_max = depth_map.min(), depth_map.max()
        if d_max - d_min < 1e-6:
            normalized = np.zeros_like(depth_map, dtype=np.uint8)
        else:
            normalized = ((depth_map - d_min) / (d_max - d_min) * 255).astype(np.uint8)

        # Apply colormap (TURBO: blue=close, red=far)
        colormap = cv2.applyColorMap(normalized, cv2.COLORMAP_TURBO)
        return colormap

    @property
    def is_available(self) -> bool:
        """Whether the depth estimator is ready."""
        return self._model is not None


# Quick test when run directly
if __name__ == "__main__":
    import time

    print("DepthEstimator Module Test")
    print("=" * 40)

    estimator = DepthEstimator()

    if not estimator.is_available:
        print("\nDepth estimator not available. Install: pip install torch torchvision timm")
        exit(1)

    print("\nStarting webcam depth test (press 'q' to quit)...")
    cap = cv2.VideoCapture(0)

    fps_start = time.time()
    fps_count = 0
    fps = 0.0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        depth_map = estimator.estimate(frame)

        # FPS counter
        fps_count += 1
        elapsed = time.time() - fps_start
        if elapsed >= 1.0:
            fps = fps_count / elapsed
            fps_count = 0
            fps_start = time.time()

        if depth_map is not None:
            colormap = estimator.get_depth_colormap(depth_map)

            # Show center distance
            h, w = frame.shape[:2]
            center_dist = estimator.get_distance_at(depth_map, w // 2, h // 2)

            cv2.putText(colormap, f"Center: {center_dist:.1f}m | FPS: {fps:.1f}",
                        (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

            cv2.imshow("Depth Map", colormap)

        cv2.imshow("Camera", frame)

        if cv2.waitKey(1) & 0xFF == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
