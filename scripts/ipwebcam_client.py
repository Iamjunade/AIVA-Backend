import asyncio
import cv2
import time
import struct
import json
import websockets
import sys

import argparse

# Configuration
# Default webcam url if none provided via command line
IP_WEBCAM_URL = "http://192.168.0.106:8080/video"
AIVA_WS_URL = "ws://127.0.0.1:8765"
AUTH_TOKEN = "aiva-dev-token-2026"
TARGET_FPS = 5

parser = argparse.ArgumentParser(description="AIVA IP Webcam Client")
parser.add_argument("--url", default=IP_WEBCAM_URL, help="IP Webcam URL (e.g. http://192.168.0.x:8080/video)")
args = parser.parse_args()
IP_WEBCAM_URL = args.url


# Protocol constants
MSG_TYPE_FRAME_DETECT = 0x01
HEADER_FORMAT = "!BII"

async def receive_responses(websocket):
    """Listen for AI processing results from the server."""
    try:
        async for message in websocket:
            data = json.loads(message)
            if data.get("type") == "frame_result":
                latency = data.get('latency_ms', 0)
                detections = data.get('detections', [])
                warnings = data.get('warnings', [])
                
                print(f"--- Frame {data.get('frame_id')} [{latency}ms] ---")
                if detections:
                    det_strs = [f"{d.get('class_name', d.get('label', 'Unknown'))} ({d.get('confidence', 0):.2f})" for d in detections]
                    print(f"Detections: {det_strs}")
                if warnings:
                    for w in warnings:
                        print(f"WARNING [{w['zone'].upper()}]: {w['message']}")
            elif data.get("type") == "error":
                print(f"SERVER ERROR: {data.get('message')}")
            elif data.get("type") == "connected":
                print(f"SERVER CONNECTED: Models Loaded = {data.get('models_loaded')}")
            else:
                print(f"Server Message: {data}")
    except websockets.exceptions.ConnectionClosed:
        print("Server connection closed.")
    except Exception as e:
        print(f"Receiver error: {e}")

async def stream_video():
    """Capture frames from IP Webcam and send to AIVA Server."""
    print(f"Starting IP Webcam Client...")
    print(f"Camera URL: {IP_WEBCAM_URL}")
    print(f"Server URL: {AIVA_WS_URL}")

    # Connect to WebSocket Server
    try:
        async with websockets.connect(
            AIVA_WS_URL,
            additional_headers={"Authorization": f"Bearer {AUTH_TOKEN}"}
        ) as websocket:
            print("Successfully connected to AIVA Server!")
            
            # Start background task to receive responses
            asyncio.create_task(receive_responses(websocket))
            
            # Open Video Stream
            cap = cv2.VideoCapture(IP_WEBCAM_URL)
            if not cap.isOpened():
                print(f"Error: Could not open video stream at {IP_WEBCAM_URL}")
                return

            frame_id = 0
            while True:
                start_time = time.time()
                ret, frame = cap.read()
                if not ret:
                    print("Error: Failed to read frame from IP Webcam.")
                    break

                # The AIVA target img size is 640. Resize to speed up network and CPU inference if needed
                frame_resized = cv2.resize(frame, (320, 240))
                
                # Compress to JPEG
                _, buffer = cv2.imencode('.jpg', frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 70])
                jpeg_bytes = buffer.tobytes()

                # Build Binary Protocol Header: msg_type (1 byte) + frame_id (4 bytes) + timestamp_ms (4 bytes)
                timestamp_ms = int(time.time() * 1000) & 0xFFFFFFFF
                header = struct.pack(HEADER_FORMAT, MSG_TYPE_FRAME_DETECT, frame_id, timestamp_ms)
                
                # Create final payload
                payload = header + jpeg_bytes

                # Send frame
                try:
                    await websocket.send(payload)
                except websockets.exceptions.ConnectionClosed as ecc:
                    print(f"Connection closed while sending. Exiting. Details: {ecc}")
                    break

                frame_id += 1

                # Throttle to TARGET_FPS
                elapsed = time.time() - start_time
                target_delay = 1.0 / TARGET_FPS
                if elapsed < target_delay:
                    await asyncio.sleep(target_delay - elapsed)

            cap.release()
            
    except ConnectionRefusedError:
        print(f"Connection refused: Is the AIVA Server running at {AIVA_WS_URL}?")
    except Exception as e:
        print(f"Streaming error: {e}")

if __name__ == '__main__':
    try:
        asyncio.run(stream_video())
    except KeyboardInterrupt:
        print("Stopped by user. Press Ctrl+C again to abort immediately.")
    except Exception as e:
        import traceback
        traceback.print_exc()
