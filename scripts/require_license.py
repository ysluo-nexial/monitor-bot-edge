#!/usr/bin/env python3
"""Exit non-zero if this machine has no valid local license."""
from __future__ import annotations

import json
import sys
from pathlib import Path

LICENSE_PATH = Path(__file__).resolve().parents[1] / "license" / "license.json"


def main() -> int:
    if not LICENSE_PATH.exists():
        print("No license. Run: python scripts/activate.py", file=sys.stderr)
        return 1
    data = json.loads(LICENSE_PATH.read_text(encoding="utf-8"))
    if not data.get("license_token"):
        print("License file missing license_token", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
