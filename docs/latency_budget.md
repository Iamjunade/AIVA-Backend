# AIVA Latency Budget (Revised)

**Target**: < 700ms Round-Trip Time (RTT) @ 95th Percentile
**Constraint**: Safety-Critical (Stop command must arrive before impact).

## Breakdown

| Stage | Component | Budget (ms) | Notes |
|-------|-----------|-------------|-------|
| **1. Capture** | CameraX + YUV Access | 30ms | 640x480 @ 30fps |
| **2. Encode** | YUV → JPEG (Q75) | 70ms | Can spike to 90ms on mid-range |
| **3. Network Up** | 4G/5G Upload | 120ms | 40-70KB payload avg |
| **4. Server Queue** | Request Handling | 10ms | Async server |
| **5. AI Inference** | YOLO + MiDaS | 300ms | GPU (Laptop) |
| **6. Logic** | Spatial Engine | 5ms | CPU (Laptop) |
| **7. Network Down** | JSON Download | 50ms | Small payload |
| **8. Client Logic** | JSON Parse + TTS Trigger | 20ms | Mobile CPU |
| **9. Audio** | TTS Buffering + Speaker | 100ms | Warm engine on launch |
| **TOTAL** | | **705ms** | **Focus needed on Stage 3 & 5** |

## Optimization Rules

1.  **Resolution**: Strict **640x480**. Higher resolution explodes Stage 2 (Encode) and Stage 3 (Upload).
2.  **Compression**: JPEG Quality **75**. Good balance of size vs artifacting for AI.
3.  **No Queueing**: If Stage 3 (Network Up) is slow, drop frames at Stage 2. Never buffer.
4.  **Audio**: Warm up TTS engine on app launch to avoid first-utterance lag.
