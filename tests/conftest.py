"""
AIVA Test Suite — Shared Fixtures
====================================
pytest fixtures used across all test modules.

Provides:
    - Dummy JPEG bytes (valid, decodable by OpenCV)
    - Binary frame packet with correct AIVA header
    - Mock FrameProcessor (bypasses 500MB+ model loading)
    - Async WebSocket server for integration tests
"""

import struct
import pytest
import numpy as np
import cv2


# =============================================================================
# JPEG FIXTURE
# =============================================================================

@pytest.fixture
def dummy_jpeg() -> bytes:
    """Create a valid JPEG image (100x100 blue) for testing."""
    frame = np.zeros((100, 100, 3), dtype=np.uint8)
    frame[:, :] = (255, 128, 0)  # BGR blue-ish
    _, buf = cv2.imencode(".jpg", frame)
    return buf.tobytes()


@pytest.fixture
def dummy_frame() -> np.ndarray:
    """Create a valid BGR numpy frame (480x640) for testing."""
    return np.zeros((480, 640, 3), dtype=np.uint8)


# =============================================================================
# BINARY PACKET FIXTURE (matches Android FramePacketizer format)
# =============================================================================

@pytest.fixture
def frame_packet(dummy_jpeg) -> bytes:
    """Build a binary frame packet with AIVA header (9 bytes) + JPEG payload."""
    msg_type = 0x01  # FRAME_DETECT
    frame_id = 42
    timestamp_ms = 123456789
    header = struct.pack("!BII", msg_type, frame_id, timestamp_ms)
    return header + dummy_jpeg


@pytest.fixture
def ocr_packet(dummy_jpeg) -> bytes:
    """Build a binary OCR frame packet."""
    msg_type = 0x02  # FRAME_OCR
    frame_id = 7
    timestamp_ms = 100000
    header = struct.pack("!BII", msg_type, frame_id, timestamp_ms)
    return header + dummy_jpeg


@pytest.fixture
def ping_packet() -> bytes:
    """Build a binary PING packet (no JPEG payload needed)."""
    msg_type = 0x10  # PING
    frame_id = 0
    timestamp_ms = 0
    header = struct.pack("!BII", msg_type, frame_id, timestamp_ms)
    return header
