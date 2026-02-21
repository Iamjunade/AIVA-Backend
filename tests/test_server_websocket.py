"""
Tests for AIVA WebSocket Server — Integration Test (Mocked Processor)
======================================================================
Starts a real WebSocket server with a mocked FrameProcessor,
sends binary frame packets, and validates JSON responses.

Requires: pytest-asyncio, websockets
"""

import json
import struct
import asyncio
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, patch, AsyncMock

import websockets

from server.protocol import FrameResponse, ConnectedResponse


# =============================================================================
# SERVER FIXTURE
# =============================================================================

@pytest_asyncio.fixture
async def mock_server():
    """
    Start a real WebSocket server on a random port with mocked processor.
    Yields (host, port) for the test client to connect to.
    """
    from server.aiva_server import AIVAServer

    # Create server with mocked processor
    server = object.__new__(AIVAServer)
    server._processor = MagicMock()
    server._processor.is_ready = True
    server._processor.models_status = {
        "yolo": True, "midas": True, "ocr": True, "faces": False
    }
    server._processor.process.return_value = FrameResponse(
        frame_id=42,
        latency_ms=50,
        detections=[{"class": "person", "confidence": 0.85}],
        warnings=[],
        surroundings="A person 3.0 meters ahead.",
    )

    # Mock auth to always pass
    server._auth = MagicMock()
    server._auth.validate_token = MagicMock()
    server._auth.extract_token = MagicMock(return_value="valid-token")

    server._rate_limiter = MagicMock()
    server._rate_limiter.check = MagicMock(return_value=True)
    server._rate_limiter.remove_client = MagicMock()

    server._active_connections = 0
    server._max_connections = 2

    # Start server on random available port
    host = "127.0.0.1"
    port = 0  # Will bind to random available port

    async def handler(websocket):
        """Simplified handler that mirrors aiva_server logic."""
        # Send connected response
        connected = ConnectedResponse(
            models_loaded=server._processor.is_ready
        )
        await websocket.send(json.dumps(connected.to_dict()))

        async for message in websocket:
            if isinstance(message, bytes):
                resp = server._processor.process(message[9:], 0x01, frame_id=42)
                await websocket.send(json.dumps(resp.to_dict()))

    ws_server = await websockets.serve(handler, host, 0)
    actual_port = ws_server.sockets[0].getsockname()[1]

    yield host, actual_port

    ws_server.close()
    await ws_server.wait_closed()


# =============================================================================
# INTEGRATION TESTS
# =============================================================================

@pytest.mark.asyncio
class TestWebSocketIntegration:
    """End-to-end WebSocket tests with mocked pipeline."""

    async def test_connect_receives_connected_message(self, mock_server):
        host, port = mock_server
        async with websockets.connect(f"ws://{host}:{port}") as ws:
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            assert msg["type"] == "connected"
            assert msg["models_loaded"] is True

    async def test_send_frame_receives_response(self, mock_server, dummy_jpeg):
        host, port = mock_server
        header = struct.pack("!BII", 0x01, 42, 100000)
        packet = header + dummy_jpeg

        async with websockets.connect(f"ws://{host}:{port}") as ws:
            # Consume connected message
            await asyncio.wait_for(ws.recv(), timeout=5)
            # Send frame
            await ws.send(packet)
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            assert msg["type"] == "frame_result"
            assert msg["frame_id"] == 42
            assert len(msg["detections"]) >= 1

    async def test_response_has_required_fields(self, mock_server, dummy_jpeg):
        host, port = mock_server
        header = struct.pack("!BII", 0x01, 1, 50000)
        packet = header + dummy_jpeg

        async with websockets.connect(f"ws://{host}:{port}") as ws:
            await asyncio.wait_for(ws.recv(), timeout=5)
            await ws.send(packet)
            raw = await asyncio.wait_for(ws.recv(), timeout=5)
            msg = json.loads(raw)
            required = ["type", "frame_id", "latency_ms", "detections",
                        "warnings", "surroundings", "faces"]
            for field in required:
                assert field in msg, f"Missing field: {field}"
