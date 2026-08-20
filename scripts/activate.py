#!/usr/bin/env python3
"""Activate this machine with a product key from the license server.

No recognition starts until activate succeeds and license/license.json exists.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LICENSE_PATH = ROOT / "license" / "license.json"


def main() -> int:
    server = os.environ.get("LICENSE_SERVER_URL", "").rstrip("/")
    product_key = os.environ.get("PRODUCT_KEY", "")
    if not server or not product_key:
        print("Set LICENSE_SERVER_URL and PRODUCT_KEY", file=sys.stderr)
        return 2

    machine_id = os.environ.get("MACHINE_ID") or _machine_id()
    body = json.dumps(
        {"product_key": product_key, "machine_id": machine_id}
    ).encode()
    req = urllib.request.Request(
        f"{server}/api/edge/activate",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        print(f"activate failed: HTTP {exc.code}", file=sys.stderr)
        return 1
    except urllib.error.URLError as exc:
        print(f"activate failed: {exc.reason}", file=sys.stderr)
        return 1

    LICENSE_PATH.parent.mkdir(parents=True, exist_ok=True)
    LICENSE_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"license written to {LICENSE_PATH}")
    return 0


def _machine_id() -> str:
    node = Path("/etc/machine-id")
    if node.exists():
        return node.read_text(encoding="utf-8").strip()
    return os.environ.get("COMPUTERNAME", "unknown-machine")


if __name__ == "__main__":
    raise SystemExit(main())
