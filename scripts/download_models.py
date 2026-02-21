"""
AIVA — Deterministic Model Pre-Download
==========================================
Executed during Docker build to bake all model weights into the image.

Downloads:
    - YOLOv8n         (~6.2 MB)   → /app/models/yolov8n.pt
    - MiDaS Small     (~50 MB)    → torch hub cache
    - Whisper Small    (~461 MB)   → whisper cache
    - EasyOCR English  (~100 MB)   → ~/.EasyOCR/model

Total: ~620 MB compressed → ensures zero-latency cold start.

Usage:
    python scripts/download_models.py            # Downloads all
    python scripts/download_models.py --verify    # Verify cached models
"""

import argparse
import os
import sys
import time
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
MODELS_DIR = PROJECT_ROOT / "models"


def download_yolo() -> None:
    """Download YOLOv8n object detection model."""
    print("[1/4] Downloading YOLOv8n ...")
    from ultralytics import YOLO

    model_path = MODELS_DIR / "yolov8n.pt"
    if model_path.exists():
        print(f"  ✓ Already cached: {model_path} ({model_path.stat().st_size / 1e6:.1f} MB)")
        return

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    model = YOLO("yolov8n.pt")
    # Ultralytics downloads to CWD; move to models/
    src = Path("yolov8n.pt")
    if src.exists() and not model_path.exists():
        src.rename(model_path)
    print(f"  ✓ Downloaded: {model_path}")


def download_midas() -> None:
    """Download MiDaS Small depth estimation model to torch hub cache."""
    print("[2/4] Downloading MiDaS Small ...")
    import torch

    cache_dir = Path(torch.hub.get_dir()) / "checkpoints"
    # Check if already cached
    cached_files = list(cache_dir.glob("*midas*")) if cache_dir.exists() else []
    if cached_files:
        print(f"  ✓ Already cached in torch hub ({len(cached_files)} files)")
        return

    model = torch.hub.load("intel-isl/MiDaS", "MiDaS_small", trust_repo=True)
    model.eval()
    del model
    print("  ✓ Downloaded MiDaS Small to torch hub cache")


def download_whisper() -> None:
    """Download Whisper Small speech recognition model."""
    print("[3/4] Downloading Whisper Small ...")
    try:
        import whisper

        model_dir = Path.home() / ".cache" / "whisper"
        cached = list(model_dir.glob("small*")) if model_dir.exists() else []
        if cached:
            print(f"  ✓ Already cached: {cached[0]}")
            return

        model = whisper.load_model("small", download_root=str(model_dir))
        del model
        print("  ✓ Downloaded Whisper Small")
    except ImportError:
        print("  ⚠ openai-whisper not installed — skipping")


def download_easyocr() -> None:
    """Download EasyOCR English model."""
    print("[4/4] Downloading EasyOCR English ...")
    try:
        import easyocr

        # EasyOCR downloads on first Reader() instantiation
        reader = easyocr.Reader(["en"], gpu=False, verbose=False)
        del reader
        print("  ✓ Downloaded EasyOCR English model")
    except ImportError:
        print("  ⚠ easyocr not installed — skipping")


def verify_models() -> None:
    """Verify all expected models are cached."""
    import torch

    checks = {
        "YOLOv8n": MODELS_DIR / "yolov8n.pt",
        "MiDaS (torch hub)": Path(torch.hub.get_dir()),
        "Whisper cache": Path.home() / ".cache" / "whisper",
        "EasyOCR cache": Path.home() / ".EasyOCR" / "model",
    }

    print("\n=== Model Verification ===")
    all_ok = True
    for name, path in checks.items():
        exists = path.exists()
        status = "✓" if exists else "✗"
        size = ""
        if exists and path.is_file():
            size = f" ({path.stat().st_size / 1e6:.1f} MB)"
        elif exists and path.is_dir():
            total = sum(f.stat().st_size for f in path.rglob("*") if f.is_file())
            size = f" ({total / 1e6:.1f} MB total)"
        print(f"  {status} {name}: {path}{size}")
        if not exists:
            all_ok = False

    if all_ok:
        print("\n✓ All models verified")
    else:
        print("\n✗ Some models missing — run without --verify to download")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="AIVA Model Pre-Download")
    parser.add_argument("--verify", action="store_true", help="Verify cached models only")
    args = parser.parse_args()

    if args.verify:
        verify_models()
        return

    print("=" * 50)
    print("AIVA Model Pre-Download")
    print("=" * 50)
    start = time.time()

    download_yolo()
    download_midas()
    download_whisper()
    download_easyocr()

    elapsed = time.time() - start
    print(f"\nAll models downloaded in {elapsed:.1f}s")
    print("Run with --verify to confirm.")


if __name__ == "__main__":
    main()
