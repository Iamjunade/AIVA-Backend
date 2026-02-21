"""
Tests for AIVA Server Protocol — Message Parsing & Response Serialization
"""

import struct
import pytest

from server.protocol import (
    MessageType,
    FrameRequest,
    FrameResponse,
    ErrorResponse,
    ConnectedResponse,
    DetectionResult,
    WarningResult,
    HEADER_SIZE,
    HEADER_FORMAT,
    ErrorCode,
)


# =============================================================================
# HEADER FORMAT
# =============================================================================

class TestHeaderFormat:
    """Validate the binary header constants."""

    def test_header_size_is_9(self):
        assert HEADER_SIZE == 9, "Header must be exactly 9 bytes (1+4+4)"

    def test_header_struct_format(self):
        assert HEADER_FORMAT == "!BII"

    def test_message_type_values(self):
        assert MessageType.FRAME_DETECT == 0x01
        assert MessageType.FRAME_OCR == 0x02
        assert MessageType.FRAME_DESCRIBE == 0x03
        assert MessageType.PING == 0x10


# =============================================================================
# FrameRequest.from_bytes
# =============================================================================

class TestFrameRequestParsing:
    """Tests for FrameRequest.from_bytes()."""

    def test_valid_detect_frame(self, frame_packet):
        req = FrameRequest.from_bytes(frame_packet)
        assert req.msg_type == MessageType.FRAME_DETECT
        assert req.frame_id == 42
        assert req.client_timestamp_ms == 123456789
        assert len(req.jpeg_bytes) > 100

    def test_valid_ocr_frame(self, ocr_packet):
        req = FrameRequest.from_bytes(ocr_packet)
        assert req.msg_type == MessageType.FRAME_OCR
        assert req.frame_id == 7

    def test_valid_ping(self, ping_packet):
        req = FrameRequest.from_bytes(ping_packet)
        assert req.msg_type == MessageType.PING
        assert req.frame_id == 0

    def test_too_short_raises(self):
        with pytest.raises(ValueError, match="too short"):
            FrameRequest.from_bytes(b"\x01\x00")

    def test_unknown_type_raises(self):
        header = struct.pack("!BII", 0xFF, 1, 1000)
        with pytest.raises(ValueError, match="Unknown message type"):
            FrameRequest.from_bytes(header + b"\x00" * 200)

    def test_empty_jpeg_raises(self):
        """JPEG payload < 100 bytes for non-PING should raise."""
        header = struct.pack("!BII", 0x01, 1, 1000)
        tiny_payload = b"\x00" * 50
        with pytest.raises(ValueError, match="too small"):
            FrameRequest.from_bytes(header + tiny_payload)

    def test_ping_allows_empty_payload(self, ping_packet):
        """PING messages don't need a JPEG payload."""
        req = FrameRequest.from_bytes(ping_packet)
        assert len(req.jpeg_bytes) == 0

    def test_received_at_is_populated(self, frame_packet):
        req = FrameRequest.from_bytes(frame_packet)
        assert req.received_at > 0


# =============================================================================
# RESPONSE SERIALIZATION
# =============================================================================

class TestFrameResponse:
    """Tests for FrameResponse.to_dict()."""

    def test_default_values(self):
        resp = FrameResponse()
        d = resp.to_dict()
        assert d["type"] == "frame_result"
        assert d["frame_id"] == 0
        assert d["detections"] == []
        assert d["warnings"] == []
        assert d["faces"] == []
        assert d["ocr_text"] is None
        assert d["surroundings"] is None

    def test_populated_response(self):
        resp = FrameResponse(
            frame_id=42,
            latency_ms=150,
            detections=[{"class": "person", "confidence": 0.85}],
            warnings=[{"message": "Stop!", "priority": 0}],
            faces=["Pasha"],
            ocr_text="Hello World",
            surroundings="A person 2.0 meters ahead.",
        )
        d = resp.to_dict()
        assert d["frame_id"] == 42
        assert d["latency_ms"] == 150
        assert len(d["detections"]) == 1
        assert d["faces"] == ["Pasha"]
        assert d["ocr_text"] == "Hello World"


class TestErrorResponse:
    """Tests for ErrorResponse.to_dict()."""

    def test_default_type(self):
        err = ErrorResponse()
        assert err.to_dict()["type"] == "error"

    def test_with_code_and_message(self):
        err = ErrorResponse(
            frame_id=5,
            code=ErrorCode.DECODE_FAILED,
            message="Invalid JPEG"
        )
        d = err.to_dict()
        assert d["code"] == "DECODE_FAILED"
        assert d["message"] == "Invalid JPEG"
        assert d["frame_id"] == 5


class TestConnectedResponse:
    """Tests for ConnectedResponse.to_dict()."""

    def test_default_values(self):
        resp = ConnectedResponse()
        d = resp.to_dict()
        assert d["type"] == "connected"
        assert d["server_version"] == "1.0.0"
        assert d["models_loaded"] is False

    def test_models_loaded_flag(self):
        resp = ConnectedResponse(models_loaded=True)
        assert resp.to_dict()["models_loaded"] is True
