#!/usr/bin/env python
"""Seed / reseed the HR demo database."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from backend.app.db.seed import seed  # noqa: E402

if __name__ == "__main__":
    force = "--force" in sys.argv
    seed(force=force)
