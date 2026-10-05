#!/usr/bin/env python
"""Start the Streamlit chat UI."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
app = ROOT / "frontend" / "streamlit_app.py"

if __name__ == "__main__":
    raise SystemExit(subprocess.call([sys.executable, "-m", "streamlit", "run", str(app), "--server.port", "8501"]))
