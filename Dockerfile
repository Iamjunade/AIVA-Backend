# =============================================================================
# AIVA Server — Production GPU Dockerfile
# =============================================================================
# Multi-stage build that bakes all AI model weights (~620MB) into the image
# during CI, ensuring zero-latency cold start for the application container.
#
# Build:
#   docker build -t aiva-server:latest .
#
# Run:
#   docker run --gpus all -p 8765:8765 --env-file .env aiva-server:latest
#
# Image layers:
#   Stage 1 (model-downloader): Downloads YOLOv8n, MiDaS, Whisper, EasyOCR
#   Stage 2 (runtime):          Copies baked weights + app code
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1: Model Downloader (discarded after build — weights survive via COPY)
# ---------------------------------------------------------------------------
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04 AS model-downloader

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip python3.10-venv git libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build

# Install Python deps needed for model download
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy download script and run it
COPY scripts/download_models.py scripts/download_models.py
RUN python3 scripts/download_models.py

# Verify all models are cached
RUN python3 scripts/download_models.py --verify


# ---------------------------------------------------------------------------
# Stage 2: Runtime (lean image with baked models)
# ---------------------------------------------------------------------------
FROM nvidia/cuda:12.2.2-runtime-ubuntu22.04 AS runtime

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV NVIDIA_VISIBLE_DEVICES=all
ENV NVIDIA_DRIVER_CAPABILITIES=compute,utility

# System deps (minimal — no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3.10 python3-pip libgl1 libglib2.0-0 libsm6 libxext6 \
    && rm -rf /var/lib/apt/lists/* \
    && ln -sf /usr/bin/python3.10 /usr/bin/python

WORKDIR /app

# Install Python dependencies
COPY requirements.txt .
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy baked model weights from Stage 1
COPY --from=model-downloader /build/models/ /app/models/
COPY --from=model-downloader /root/.cache/ /root/.cache/
COPY --from=model-downloader /root/.EasyOCR/ /root/.EasyOCR/

# Copy application code
COPY server/ server/
COPY src/ src/
COPY main.py .
COPY .env.example .env.example

# Health check (verifies WebSocket port is open)
HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
    CMD python -c "import socket; s=socket.socket(); s.settimeout(2); s.connect(('127.0.0.1',8765)); s.close()" || exit 1

# Expose WebSocket port
EXPOSE 8765

# Run server
CMD ["python", "-m", "server"]
