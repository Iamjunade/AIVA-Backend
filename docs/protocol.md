# AIVA Protocol Specification v1.1

## Overview
This document defines the communication protocol between the Android Client (Mobile) and the Python Server (Laptop/Cloud).
The protocol uses **WebSockets** (WSS) and is designed for low-latency video streaming.

## WebSocket Connection
- **URL**: `wss://<server-host>/ws`
- **Auth**: Bearer Token in HTTP Headers (`Authorization: Bearer <token>`)
- **Policy**: Max **1 connection per token**. Rejects duplicate tokens.
- **Heartbeat**: Ping/Pong every 5s.

---

## Client -> Server (Binary Frame)

The client sends video frames as **Binary Messages**.
Total Header Size: **10 Bytes**.
Byte Order: **Big Endian**.

| Offset | Size | Type | Description | Value |
|--------|------|------|-------------|-------|
| 0 | 1 | uint8 | Protocol Version | `0x01` |
| 1 | 1 | uint8 | Message Type | `0x01` (Video Frame) |
| 2 | 4 | uint32 | Frame ID | Incremental counter |
| 6 | 4 | uint32 | Timestamp (ms) | Relative time since app start (uint32) |
| 10 | N | bytes | Payload | JPEG Image Data (Max 200KB) |

**Refinements:**
- **Relative Timestamp**: Use `SystemClock.elapsedRealtime()` on Android (uint32 safe). Avoids overflow risk for years.
- **Max Payload**: 200KB hard limit. Q75 640x480 typically 40-70KB.
- **Drop Detection**: Client tracks acked `frame_id`. Missing sequence = Drop.

---

## Server -> Client (JSON Response)

The server sends analysis results as **Text Messages (JSON)**.

### Detection Result (`frame_result`)
Sent for every processed frame.

```json
{
  "type": "frame_result",
  "frame_id": 12345,
  "timestamp_ms": 5000,
  "latency_ms": 150,
  "detections": [
    {
      "class": "person",
      "confidence": 0.95,
      "bbox": [100, 100, 200, 300],
      "distance_m": 2.5,
      "direction": "center"
    }
  ],
  "warnings": [
    {
      "action": "STOP",
      "object": "car",
      "priority": "danger",
      "zone": "danger",
      "distance": 1.0
    }
  ],
  "ocr_text": "EXIT"  // Optional
}
```

### Warning Structure
Client constructs TTS message deterministically:
- `action`: STOP | CAUTION | INFO
- `object`: "car", "stairs", etc.
- `priority`: danger | caution | info

### Connection Status (`connected`)
Sent immediately after successful authentication.

```json
{
  "type": "connected",
  "server_version": "1.0",
  "models_loaded": true
}
```

---

## Client Behavior Rules

1.  **Drop Policy**: If WebSocket calls `send()` and buffer is full, or state is not `CONNECTED`, drop the frame immediately. Do NOT queue video frames.
2.  **Reconnect**: Use exponential backoff (1s, 2s, 4s... 30s).
3.  **Safety Fallback**: If connection drops, TTS must announce "Connection lost".
