"""
AIVA Server — OCR Engine (EasyOCR)
=====================================
Offline text reading using EasyOCR with GPU acceleration.

Design Constraints:
    - User-triggered ONLY — never auto-invoked during navigation
    - Confidence threshold ≥ 0.65
    - Returns exact text as captured — no summarization
    - No interpretation unless explicitly requested
    - Language: English (preloaded)
"""

import time
from typing import List, Optional, Tuple

import cv2
import numpy as np

try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False
    print("[OCREngine] WARNING: easyocr not installed. Run: pip install easyocr")

from server.config import OCR_LANGUAGES, OCR_CONFIDENCE_THRESHOLD, OCR_GPU


class OCREngine:
    """
    EasyOCR wrapper for offline text reading.

    Loads EasyOCR reader with GPU acceleration on initialization.
    Exposes a single read() method that returns detected text
    exactly as captured, with no summarization.

    This engine is designed to be called ONLY when the user
    explicitly requests text reading ("Read this", "What does it say?").
    It must NEVER be auto-invoked in the detection loop.
    """

    def __init__(
        self,
        languages: Optional[List[str]] = None,
        confidence_threshold: float = OCR_CONFIDENCE_THRESHOLD,
        use_gpu: bool = OCR_GPU
    ):
        """
        Initialize the OCR engine.

        Args:
            languages: List of language codes (default: ["en"])
            confidence_threshold: Minimum confidence for text detection (≥ 0.65)
            use_gpu: Use GPU acceleration if available
        """
        self._reader = None
        self._confidence_threshold = max(confidence_threshold, 0.65)
        self._languages = languages or OCR_LANGUAGES

        if not EASYOCR_AVAILABLE:
            print("[OCREngine] Disabled — easyocr not installed")
            return

        self._load_reader(use_gpu)

    def _load_reader(self, use_gpu: bool) -> None:
        """Load the EasyOCR reader."""
        try:
            print(f"[OCREngine] Loading EasyOCR (languages={self._languages}, "
                  f"gpu={use_gpu})...")
            start = time.time()

            self._reader = easyocr.Reader(
                self._languages,
                gpu=use_gpu,
                verbose=False
            )

            elapsed = (time.time() - start) * 1000
            print(f"[OCREngine] Loaded in {elapsed:.0f}ms")

        except Exception as e:
            print(f"[OCREngine] Failed to load: {e}")
            self._reader = None

    def read(self, frame: np.ndarray) -> Tuple[Optional[str], float]:
        """
        Read text from a frame.

        Returns the exact text as detected — no summarization,
        no interpretation, no creative additions.

        Args:
            frame: BGR image from OpenCV (numpy array)

        Returns:
            Tuple of (detected_text, processing_time_ms)
            detected_text is None if no text found above confidence threshold
        """
        if self._reader is None:
            return None, 0.0

        start = time.time()

        try:
            # Convert BGR to RGB for EasyOCR
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Run OCR
            results = self._reader.readtext(rgb_frame)

            # Filter by confidence threshold
            filtered = [
                (bbox, text, conf)
                for bbox, text, conf in results
                if conf >= self._confidence_threshold
            ]

            elapsed_ms = (time.time() - start) * 1000

            if not filtered:
                return None, elapsed_ms

            # Concatenate all detected text in reading order (top-to-bottom)
            # Sort by vertical position of bounding box center
            sorted_results = sorted(
                filtered,
                key=lambda r: (r[0][0][1] + r[0][2][1]) / 2  # center_y
            )

            text_lines = [text.strip() for _, text, _ in sorted_results]
            combined_text = " ".join(text_lines)

            return combined_text, elapsed_ms

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            print(f"[OCREngine] Error: {e}")
            return None, elapsed_ms

    def read_detailed(
        self, frame: np.ndarray
    ) -> Tuple[List[dict], float]:
        """
        Read text with per-region details (bounding boxes + confidence).

        Used when the client needs spatial information about text location.

        Args:
            frame: BGR image from OpenCV

        Returns:
            Tuple of (list_of_text_regions, processing_time_ms)
        """
        if self._reader is None:
            return [], 0.0

        start = time.time()

        try:
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            results = self._reader.readtext(rgb_frame)

            regions = []
            for bbox, text, conf in results:
                if conf >= self._confidence_threshold:
                    # Convert bbox to simple format
                    x_coords = [p[0] for p in bbox]
                    y_coords = [p[1] for p in bbox]
                    regions.append({
                        "text": text.strip(),
                        "confidence": round(conf, 3),
                        "bbox": [
                            int(min(x_coords)),
                            int(min(y_coords)),
                            int(max(x_coords)),
                            int(max(y_coords))
                        ]
                    })

            elapsed_ms = (time.time() - start) * 1000
            return regions, elapsed_ms

        except Exception as e:
            elapsed_ms = (time.time() - start) * 1000
            print(f"[OCREngine] Error: {e}")
            return [], elapsed_ms

    @property
    def is_available(self) -> bool:
        """Whether the OCR engine is ready."""
        return self._reader is not None

    @property
    def confidence_threshold(self) -> float:
        """Current confidence threshold."""
        return self._confidence_threshold
