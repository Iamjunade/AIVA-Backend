"""
AIVA Server — Protocol Definitions
=====================================
Message types, error codes, and dataclass definitions for the
WebSocket communication protocol between mobile client and server.

Binary Frame Format (Client → Server):
    [1 byte: msg_type] [4 bytes: frame_id (uint32)] [4 bytes: timestamp_ms (uint32)] [N bytes: JPEG]

Response Format (Server → Client):
    JSON text message (see FrameResponse dataclass)
"""

import struct
import time
from dataclasses import dataclass, field, asdict
from enum import IntEnum
from typing import Dict, List, Optional


# =============================================================================
# MESSAGE TYPES (Client → Server)
# =============================================================================

class MessageType(IntEnum):
    """Binary message type identifiers sent by the client."""
    FRAME_DETECT = 0x01    # Object detection + depth + spatial
    FRAME_OCR = 0x02       # User-triggered text reading (EasyOCR)
    FRAME_DESCRIBE = 0x03  # Scene description (Gemini, optional)
    FRAME_AUDIO = 0x04     # Voice command audio (Whisper) [legacy]
    FRAME_TEXT_QUERY = 0x05  # Pre-transcribed text query (from mobile STT)
    PING = 0x10            # Keepalive


# Binary header format: version (1 byte) + msg_type (1 byte) + frame_id (4 bytes) + timestamp_ms (4 bytes)
HEADER_FORMAT = "!BBII"  # Network byte order
HEADER_SIZE = struct.calcsize(HEADER_FORMAT)  # = 10 bytes


# =============================================================================
# ERROR CODES
# =============================================================================

class ErrorCode:
    """Server error codes returned in error responses."""
    AUTH_FAILED = "AUTH_FAILED"
    INFERENCE_TIMEOUT = "INFERENCE_TIMEOUT"
    DECODE_FAILED = "DECODE_FAILED"
    SERVER_OVERLOADED = "SERVER_OVERLOADED"
    MODEL_UNAVAILABLE = "MODEL_UNAVAILABLE"
    INVALID_MESSAGE = "INVALID_MESSAGE"
    RATE_LIMITED = "RATE_LIMITED"


# =============================================================================
# REQUEST PARSING
# =============================================================================

@dataclass
class FrameRequest:
    """Parsed binary frame request from the client."""
    msg_type: MessageType
    frame_id: int
    client_timestamp_ms: int
    payload_bytes: bytes  # JPEG or Audio
    received_at: float = field(default_factory=time.time)

    @staticmethod
    def from_bytes(data: bytes) -> "FrameRequest":
        """
        Parse a binary WebSocket message into a FrameRequest.

        Args:
            data: Raw binary message bytes

        Returns:
            Parsed FrameRequest

        Raises:
            ValueError: If message is too short or has invalid type
        """
        if len(data) < HEADER_SIZE:
            raise ValueError(
                f"Message too short: {len(data)} bytes, "
                f"minimum {HEADER_SIZE} required"
            )

        version_raw, msg_type_raw, frame_id, timestamp_ms = struct.unpack(
            HEADER_FORMAT, data[:HEADER_SIZE]
        )

        # Validate message type
        try:
            msg_type = MessageType(msg_type_raw)
        except ValueError:
            raise ValueError(f"Unknown message type: 0x{msg_type_raw:02X}")

        payload_bytes = data[HEADER_SIZE:]

        if msg_type not in (MessageType.PING, MessageType.FRAME_TEXT_QUERY) and len(payload_bytes) < 10:
            raise ValueError(
                f"Payload too small: {len(payload_bytes)} bytes "
                f"(likely corrupt or empty)"
            )

        # Text queries just need at least 1 byte of text
        if msg_type == MessageType.FRAME_TEXT_QUERY and len(payload_bytes) < 1:
            raise ValueError("Text query payload is empty")

        return FrameRequest(
            msg_type=msg_type,
            frame_id=frame_id,
            client_timestamp_ms=timestamp_ms,
            payload_bytes=payload_bytes,
        )


# =============================================================================
# RESPONSE DATACLASSES
# =============================================================================

@dataclass
class DetectionResult:
    """A single detected object in the response."""
    class_name: str
    confidence: float
    distance_m: Optional[float]
    direction: Optional[str]
    bbox: List[int]  # [x1, y1, x2, y2]


@dataclass
class WarningResult:
    """A spatial warning in the response."""
    message: str
    priority: int           # Lower = more urgent
    is_critical: bool       # True = DANGER zone (< 1.2m)
    zone: str               # "caution" or "danger"


@dataclass
class FrameResponse:
    """
    Complete server response for a processed frame.

    Serialized to JSON and sent as a text WebSocket message.
    """
    type: str = "frame_result"
    frame_id: int = 0
    timestamp_ms: int = 0
    latency_ms: int = 0
    detections: List[Dict] = field(default_factory=list)
    warnings: List[Dict] = field(default_factory=list)
    surroundings: Optional[str] = None
    ocr_text: Optional[str] = None
    faces: List[str] = field(default_factory=list)
    unknown_faces_count: int = 0
    danger_summary: Optional[str] = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dictionary."""
        return asdict(self)


@dataclass
class CommandResponse:
    """
    High-priority command sent to client.
    Triggers immediate action (SOS, Location, etc.).
    """
    type: str = "command"
    action: str = ""       # "SOS", "LOCATION", "READ_BATTERY"
    params: Dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class SpeechResponse:
    """
    Speech response sent to the client to be spoken via Text-To-Speech.
    """
    text: str
    type: str = "speech"
    
    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ErrorResponse:
    """Error response sent to client."""
    type: str = "error"
    frame_id: int = 0
    code: str = ""
    message: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ConnectedResponse:
    """Sent on successful WebSocket connection."""
    type: str = "connected"
    server_version: str = "1.0.0"
    models_loaded: bool = False

    def to_dict(self) -> dict:
        return asdict(self)
