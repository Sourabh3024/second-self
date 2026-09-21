#!/usr/bin/env python3
"""Ask questions against the SecondSelf wiki."""

from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from secondself.ask import main


if __name__ == "__main__":
    main()
