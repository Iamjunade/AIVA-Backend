"""
AIVA Server — Configuration
==============================
Centralized server configuration. All tunable parameters in one place.

Values loaded from environment variables where appropriate,
with sensible defaults for development.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load .env from project root
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(_PROJECT_ROOT / ".env")


# =============================================================================
# SERVER NETWORK
# =============================================================================

SERVER_HOST = os.getenv("AIVA_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("AIVA_PORT", "8765"))

# Maximum concurrent client connections (resource protection)
MAX_CLIENTS = int(os.getenv("AIVA_MAX_CLIENTS", "2"))


# =============================================================================
# SECURITY
# =============================================================================

# Static bearer token (legacy — kept for backwards compatibility)
AUTH_TOKEN = os.getenv("AIVA_AUTH_TOKEN", "aiva-dev-token-2026")

# JWT Configuration (production authentication)
JWT_SECRET = os.getenv("AIVA_JWT_SECRET", "")  # REQUIRED in production
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = int(os.getenv("AIVA_JWT_EXPIRY_HOURS", "24"))
JWT_REFRESH_WINDOW_HOURS = int(os.getenv("AIVA_JWT_REFRESH_HOURS", "48"))
JWT_ISSUER = "aiva-server"

# Authentication mode: "jwt" (production) or "static" (development)
AUTH_MODE = os.getenv("AIVA_AUTH_MODE", "static")

# Rate limiting: max frames per second per client
MAX_FPS_PER_CLIENT = int(os.getenv("AIVA_MAX_FPS", "30"))


# =============================================================================
# LATENCY BUDGET (milliseconds)
# =============================================================================

# Total round-trip budget
LATENCY_BUDGET_TOTAL_MS = 700

# Per-stage budgets (for logging/monitoring, not hard enforcement)
LATENCY_BUDGET_YOLO_MS = 120
LATENCY_BUDGET_MIDAS_MS = 150
LATENCY_BUDGET_OCR_MS = 200
LATENCY_BUDGET_SPATIAL_MS = 5

# Server-side processing timeout (hard cutoff)
PROCESSING_TIMEOUT_MS = 650  # Leave 50ms for network


# =============================================================================
# DETECTION MODEL
# =============================================================================

YOLO_MODEL = os.getenv("AIVA_YOLO_MODEL", "yolov8n.pt")
YOLO_CONFIDENCE = float(os.getenv("AIVA_YOLO_CONFIDENCE", "0.6"))
YOLO_IMG_SIZE = int(os.getenv("AIVA_YOLO_IMG_SIZE", "640"))


# =============================================================================
# DEPTH ESTIMATION
# =============================================================================

MIDAS_MODEL = os.getenv("AIVA_MIDAS_MODEL", "MiDaS_small")
MIDAS_DEPTH_SCALE = float(os.getenv("AIVA_MIDAS_DEPTH_SCALE", "2.5"))

# Frame skip: run MiDaS every Nth frame (cache depth between runs)
MIDAS_FRAME_SKIP = int(os.getenv("AIVA_MIDAS_SKIP", "3"))

# Motion-delta threshold: if any detected object's bbox area grows
# by more than this factor between frames, force immediate depth refresh
MIDAS_MOTION_DELTA_THRESHOLD = float(
    os.getenv("AIVA_MIDAS_MOTION_THRESHOLD", "1.4")
)  # 40% area growth = object approaching fast


# =============================================================================
# OBSTACLE THRESHOLDS (dual-threshold system)
# =============================================================================

# Tier 1: Caution zone — early warning
CAUTION_DISTANCE_M = float(os.getenv("AIVA_CAUTION_DISTANCE", "1.5"))

# Tier 2: Danger zone — immediate stop
DANGER_DISTANCE_M = float(os.getenv("AIVA_DANGER_DISTANCE", "1.2"))


# =============================================================================
# OCR (EasyOCR)
# =============================================================================

OCR_LANGUAGES = ["en"]
OCR_CONFIDENCE_THRESHOLD = float(os.getenv("AIVA_OCR_CONFIDENCE", "0.65"))
# OCR is user-triggered only — never auto-invoked in detection loop
OCR_GPU = True  # Use GPU acceleration


# =============================================================================
# GEMINI (Optional — isolated, never in navigation loop)
# =============================================================================

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
GEMINI_MODEL = os.getenv("AIVA_GEMINI_MODEL", "gemini-2.0-flash")


# =============================================================================
# FACE RECOGNITION
# =============================================================================

KNOWN_FACES_DIR = str(_PROJECT_ROOT / "known_faces")
FACE_ANNOUNCE_COOLDOWN = float(os.getenv("AIVA_FACE_COOLDOWN", "30.0"))


# =============================================================================
# GDPR / PRIVACY
# =============================================================================

# Never store raw frames by default
STORE_RAW_FRAMES = False

# Log level for frame processing (excludes frame data)
LOG_LEVEL = os.getenv("AIVA_LOG_LEVEL", "INFO")
