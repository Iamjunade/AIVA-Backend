# AIVA - AI Vision Assistant

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/YOLOv8-Nano-green.svg" alt="YOLOv8">
  <img src="https://img.shields.io/badge/MiDaS-Depth-orange.svg" alt="MiDaS">
  <img src="https://img.shields.io/badge/Whisper-STT-purple.svg" alt="Whisper">
  <img src="https://img.shields.io/badge/Gemini-2.0-red.svg" alt="Gemini API">
</p>

**AIVA** (AI Vision Assistant) is a real-time AI-powered assistant designed to enable visually impaired individuals to navigate environments independently through computer vision, spatial intelligence, and voice interaction.

**Founder:** Junaid Pasha

---

## 🌟 Features

### ✅ Phase 1 & 2: Vision + Voice + Spatial Intelligence

| Module | Capability | Technology |
|--------|-----------|------------|
| **Object Detection** | 80-class real-time detection at ≥20 FPS | YOLOv8 Nano |
| **Depth Estimation** | Approximate distance in meters + direction | MiDaS Small |
| **Spatial Intelligence** | Obstacle avoidance warnings + environment awareness | Custom engine |
| **Speech Recognition** | Offline-capable voice commands | Whisper Small |
| **Intent Classification** | Command understanding (surroundings, read, describe, emergency) | Rule-based |
| **AI Scene Description** | Cloud-based visual Q&A and OCR | Google Gemini 2.0 |
| **Face Recognition** | Local privacy-first person identification | OpenCV LBPH |
| **Text-to-Speech** | Natural voice output with adjustable speed | pyttsx3 |

### 🔒 Safety-First Design

- **Confidence threshold >0.6** — no assumption-based detections
- **Anti-hallucination** — all outputs from model inference only
- **Obstacle warnings** — automatic alerts for objects <1.5m away
- **Priority system** — vehicles > stairs > animals > persons > static objects

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                         AIVA SYSTEM                              │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   ┌─────────────┐         ┌───────────────────────────────────┐ │
│   │   Camera     │  Feed   │          Python Engine            │ │
│   │  (Webcam /   │────────▶│                                   │ │
│   │  IP Webcam)  │         │  ┌─────────────────────────────┐ │ │
│   └─────────────┘         │  │   VISION PIPELINE            │ │ │
│                           │  │  • YOLOv8 Object Detection   │ │ │
│   ┌─────────────┐         │  │  • MiDaS Depth Estimation    │ │ │
│   │  Microphone  │────────▶│  │  • Face Recognition          │ │ │
│   └─────────────┘         │  └────────────┬──────────────────┘ │ │
│                           │               ▼                    │ │
│   ┌─────────────┐         │  ┌─────────────────────────────┐ │ │
│   │   Speaker    │◀────────│  │   DECISION ENGINE            │ │ │
│   └─────────────┘         │  │  • Spatial Intelligence       │ │ │
│                           │  │  • Obstacle Avoidance         │ │ │
│                           │  │  • Intent Classification      │ │ │
│                           │  └────────────┬──────────────────┘ │ │
│                           │               ▼                    │ │
│                           │  ┌─────────────────────────────┐ │ │
│                           │  │   VOICE OUTPUT (TTS)         │ │ │
│                           │  └─────────────────────────────┘ │ │
│                           │                                   │ │
│                           │  ┌─────────────────────────────┐ │ │
│                           │  │   CLOUD AI (Gemini)    ──────┼─┼──▶ Google
│                           │  │  • Scene Description         │ │ │
│                           │  │  • OCR / Text Read           │ │ │
│                           │  └─────────────────────────────┘ │ │
│                           └───────────────────────────────────┘ │
└──────────────────────────────────────────────────────────────────┘
```

---

## ⚡ Quick Start

### 1. Clone & Setup

```bash
git clone https://github.com/yourusername/AIVA.git
cd AIVA

python -m venv venv
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure API Key

```bash
cp .env.example .env
# Edit .env: add GOOGLE_API_KEY from https://aistudio.google.com/app/apikey
```

### 3. Add Known Faces (Optional)

```
known_faces/
├── mom.jpg        → Recognized as "Mom"
├── dad.png        → Recognized as "Dad"
└── john_smith.jpg → Recognized as "John Smith"
```

### 4. Run AIVA

```bash
python main.py
```

---

## 🎮 Controls

### Keyboard (Dev/Testing)

| Key | Action |
|-----|--------|
| `v` | Voice command (listen for speech) |
| `w` | What's around me? |
| `d` | Describe scene (AI) |
| `r` | Read text (AI/OCR) |
| `m` | Toggle depth map view |
| `q` | Quit |

### Voice Commands

| Say | Action |
|-----|--------|
| "What's around me?" | List 3 nearest objects with distances |
| "Describe" / "What do you see?" | AI scene description |
| "Read text" / "Read this" | OCR text reading |
| "Emergency" / "Help" | Emergency trigger (Phase 3) |

---

## 📁 Project Structure

```
AIVA/
├── main.py                     # Main application entry point
├── requirements.txt            # Python dependencies
├── .env                        # API keys (from .env.example)
├── known_faces/                # Known face images
└── src/
    ├── __init__.py
    ├── object_detector.py      # YOLOv8 Nano object detection
    ├── depth_estimator.py      # MiDaS monocular depth estimation
    ├── spatial_engine.py       # Obstacle avoidance + environment awareness
    ├── speech_engine.py        # Whisper STT + intent + TTS
    ├── assistant_ai.py         # Gemini cloud AI (description + OCR)
    ├── face_detector.py        # Local face recognition
    └── video_stream.py         # Threaded video capture
```

---

## 💻 Hardware Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| GPU | None (CPU works) | NVIDIA GTX 1650+ with CUDA |
| RAM | 8GB | 16GB |
| CPU | 4-core | 6+ core (Ryzen 5 / i5) |
| Storage | 3GB for models | SSD recommended |
| Camera | Webcam / IP Webcam | Wide-angle preferred |
| Microphone | Any | Noise-canceling |

---

## 📊 Performance Targets (PRD KPIs)

| Metric | Target |
|--------|--------|
| Detection accuracy | >85% |
| Processing FPS | ≥20 |
| Response latency | <500ms (local), <3s (cloud AI) |
| Confidence threshold | >0.6 (enforced) |
| Crash rate | <2% |

---

## 🚀 Roadmap

- [x] **Phase 1** — Vision + Voice (Object Detection, Depth, Speech)
- [x] **Phase 2** — Spatial Intelligence (Obstacle Avoidance, Navigation)
- [ ] **Phase 3** — GPS + Emergency System
- [ ] **Phase 4** — Optimization + Beta Testing
- [ ] **Future** — Android App + Smart Glasses (Raspberry Pi 5)

---

## 🔒 Privacy & Ethics

- No cloud image storage without consent
- Face data processed locally only
- No data sold or shared
- GDPR-style compliance structure

---

<p align="center">
Made with ❤️ for accessibility | Safety > Features | Accuracy > Creativity | Reliability > Fancy UI
</p>
