"""
AIVA Server — Entry Point
============================
Allows running the server with: python -m server

Usage:
    python -m server
"""

import asyncio
import sys
from pathlib import Path

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from server.aiva_server import main

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[AIVA Server] Stopped by user")
    except Exception as e:
        print(f"[AIVA Server] Failed: {e}")
        sys.exit(1)
