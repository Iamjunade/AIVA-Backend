"""
AIVA Test Client — WebSocket Round-Trip Test
================================================
Sends test JPEG frames to the AIVA server and validates responses.

Usage:
    1. Start server: python -m server
    2. Run test:     python tests/test_ws_client.py

This simulates what the mobile client does:
    - Connect with bearer token
    - Send binary frame (JPEG with header)
    - Receive JSON response
    - Validate response structure and latency
"""

import asyncio
import json
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

try:
    import websockets
except ImportError:
    print("Install websockets: pip install websockets")
    sys.exit(1)

from server.protocol import MessageType, HEADER_FORMAT
from server.config import SERVER_PORT, AUTH_TOKEN


# =============================================================================
# TEST CLIENT
# =============================================================================

SERVER_URL = f"ws://127.0.0.1:{SERVER_PORT}"


def build_frame_message(
    msg_type: MessageType,
    jpeg_bytes: bytes,
    frame_id: int = 1,
) -> bytes:
    """
    Build a binary frame message matching the AIVA protocol.

    Format: [1 byte type][4 bytes frame_id][4 bytes timestamp_ms][JPEG bytes]
    """
    timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF  # Truncate to uint32
    header = struct.pack(HEADER_FORMAT, msg_type.value, frame_id, timestamp_ms)
    return header + jpeg_bytes


async def test_connection():
    """Test 1: Connection with authentication."""
    print("\n--- Test 1: Connection + Auth ---")

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with websockets.connect(
            SERVER_URL, additional_headers=headers
        ) as ws:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            assert data["type"] == "connected", f"Expected 'connected', got {data['type']}"
            assert data["models_loaded"] is True, "Models not loaded"

            print(f"  OK: Connected. Server v{data['server_version']}")
            print(f"  OK: Models loaded: {data['models_loaded']}")
            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        return False


async def test_invalid_auth():
    """Test 2: Connection with invalid token should be rejected."""
    print("\n--- Test 2: Invalid Auth ---")

    headers = {"Authorization": "Bearer wrong-token"}

    try:
        async with websockets.connect(
            SERVER_URL, additional_headers=headers
        ) as ws:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            assert data["type"] == "error", f"Expected error, got {data['type']}"
            assert data["code"] == "AUTH_FAILED", f"Expected AUTH_FAILED, got {data['code']}"

            print(f"  OK: Auth rejected: {data['message']}")
            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        return False


async def test_frame_detect():
    """Test 3: Send a JPEG frame for detection."""
    print("\n--- Test 3: Frame Detection ---")

    # Load test image
    test_jpg = Path(__file__).parent.parent / "test.jpg"
    if not test_jpg.exists():
        print(f"  SKIP: {test_jpg} not found")
        return None

    jpeg_bytes = test_jpg.read_bytes()
    print(f"  Sending {len(jpeg_bytes)} bytes ({len(jpeg_bytes)/1024:.0f}KB)")

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with websockets.connect(
            SERVER_URL, additional_headers=headers
        ) as ws:
            # Consume connected message
            await asyncio.wait_for(ws.recv(), timeout=5.0)

            # Send detection frame
            message = build_frame_message(
                MessageType.FRAME_DETECT,
                jpeg_bytes,
                frame_id=42,
            )
            send_time = time.time()
            await ws.send(message)

            # Receive response
            response = await asyncio.wait_for(ws.recv(), timeout=10.0)
            round_trip_ms = (time.time() - send_time) * 1000
            data = json.loads(response)

            # Validate response structure
            assert data["type"] == "frame_result", f"Expected frame_result, got {data['type']}"
            assert data["frame_id"] == 42, f"Expected frame_id 42, got {data['frame_id']}"
            assert "detections" in data
            assert "warnings" in data
            assert "latency_ms" in data

            print(f"  OK: frame_id={data['frame_id']}")
            print(f"  OK: Server latency: {data['latency_ms']}ms")
            print(f"  OK: Round-trip: {round_trip_ms:.0f}ms")
            print(f"  OK: Detections: {len(data['detections'])}")
            print(f"  OK: Warnings: {len(data['warnings'])}")

            if data['detections']:
                for det in data['detections'][:3]:
                    dist = f"{det['distance_m']}m" if det['distance_m'] else "N/A"
                    print(f"      - {det['class']} ({det['confidence']:.2f}) @ {dist} {det['direction'] or ''}")

            if data['warnings']:
                for w in data['warnings']:
                    icon = "!!" if w['is_critical'] else ">>"
                    print(f"      {icon} [{w['zone']}] {w['message']}")

            if data.get('surroundings'):
                print(f"  OK: Surroundings: {data['surroundings']}")

            # Latency check
            if round_trip_ms < 700:
                print(f"  OK: Under 700ms budget ({round_trip_ms:.0f}ms)")
            else:
                print(f"  WARNING: OVER 700ms budget ({round_trip_ms:.0f}ms)")

            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_frame_ocr():
    """Test 4: Send a JPEG frame for OCR."""
    print("\n--- Test 4: Frame OCR ---")

    test_jpg = Path(__file__).parent.parent / "test.jpg"
    if not test_jpg.exists():
        print(f"  SKIP: {test_jpg} not found")
        return None

    jpeg_bytes = test_jpg.read_bytes()
    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with websockets.connect(
            SERVER_URL, additional_headers=headers
        ) as ws:
            await asyncio.wait_for(ws.recv(), timeout=5.0)

            message = build_frame_message(
                MessageType.FRAME_OCR,
                jpeg_bytes,
                frame_id=99,
            )
            await ws.send(message)

            response = await asyncio.wait_for(ws.recv(), timeout=15.0)
            data = json.loads(response)

            assert data["frame_id"] == 99
            assert "ocr_text" in data

            print(f"  OK: OCR result: {data['ocr_text']}")
            print(f"  OK: Latency: {data['latency_ms']}ms")
            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        return False


async def test_ping():
    """Test 5: Ping keepalive."""
    print("\n--- Test 5: Ping ---")

    headers = {"Authorization": f"Bearer {AUTH_TOKEN}"}

    try:
        async with websockets.connect(
            SERVER_URL, additional_headers=headers
        ) as ws:
            await asyncio.wait_for(ws.recv(), timeout=5.0)

            # Send ping (no JPEG needed, but we need minimum header)
            ping_data = struct.pack(HEADER_FORMAT, MessageType.PING.value, 0, 0)
            await ws.send(ping_data)

            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            data = json.loads(response)

            assert data["type"] == "pong"
            print(f"  OK: Pong received (timestamp: {data['timestamp_ms']})")
            return True

    except Exception as e:
        print(f"  FAIL: {e}")
        return False


# =============================================================================
# MAIN
# =============================================================================

async def run_tests():
    """Run all test cases."""
    print("=" * 50)
    print("AIVA WebSocket Client Test")
    print(f"Server: {SERVER_URL}")
    print("=" * 50)

    results = []

    results.append(("Connection + Auth", await test_connection()))
    results.append(("Invalid Auth", await test_invalid_auth()))
    results.append(("Ping", await test_ping()))
    results.append(("Frame Detection", await test_frame_detect()))
    results.append(("Frame OCR", await test_frame_ocr()))

    print("\n" + "=" * 50)
    print("RESULTS")
    print("=" * 50)

    for name, result in results:
        if result is True:
            status = "PASS"
        elif result is False:
            status = "FAIL"
        else:
            status = "SKIP"
        print(f"  {status}: {name}")

    passed = sum(1 for _, r in results if r is True)
    total = len(results)
    print(f"\n{passed}/{total} tests passed")


if __name__ == "__main__":
    asyncio.run(run_tests())
