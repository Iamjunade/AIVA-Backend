"""
AIVA — Export MiDaS Small to ONNX
====================================
One-time script to convert the MiDaS Small model from PyTorch to ONNX.

Usage:
    python scripts/export_midas_onnx.py

Output:
    models/midas_small.onnx

Requirements:
    pip install torch torchvision timm onnx
"""

import sys
from pathlib import Path

import torch
import numpy as np

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "models"


def export_midas_to_onnx(
    model_type: str = "MiDaS_small",
    input_size: int = 256,
    output_path: Path = OUTPUT_DIR / "midas_small.onnx",
    opset_version: int = 14,
):
    """
    Export MiDaS model to ONNX format.

    Args:
        model_type: MiDaS variant to export
        input_size: Input resolution (256 for MiDaS_small)
        output_path: Where to save the .onnx file
        opset_version: ONNX opset version
    """
    print(f"Loading MiDaS model: {model_type} ...")
    model = torch.hub.load("intel-isl/MiDaS", model_type, trust_repo=True)
    model.eval()

    # Create dummy input (NCHW format)
    dummy_input = torch.randn(1, 3, input_size, input_size)

    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print(f"Exporting to ONNX (opset {opset_version}) ...")
    torch.onnx.export(
        model,
        dummy_input,
        str(output_path),
        export_params=True,
        opset_version=opset_version,
        do_constant_folding=True,
        input_names=["input"],
        output_names=["output"],
        dynamic_axes={
            "input": {0: "batch_size"},
            "output": {0: "batch_size"},
        },
    )

    # Verify file size
    size_mb = output_path.stat().st_size / (1024 * 1024)
    print(f"✓ Exported: {output_path} ({size_mb:.1f} MB)")

    # Quick validation with ONNX Runtime
    try:
        import onnxruntime as ort

        session = ort.InferenceSession(str(output_path))
        input_name = session.get_inputs()[0].name
        output = session.run(None, {input_name: dummy_input.numpy()})
        print(f"✓ ONNX Runtime validation passed (output shape: {output[0].shape})")
    except ImportError:
        print("⚠ onnxruntime not installed — skipping validation")
    except Exception as e:
        print(f"✗ ONNX Runtime validation failed: {e}")
        sys.exit(1)

    print("\nDone! Use in code:")
    print("  from src.depth_estimator_onnx import DepthEstimatorONNX")
    print("  estimator = DepthEstimatorONNX()")


if __name__ == "__main__":
    export_midas_to_onnx()
