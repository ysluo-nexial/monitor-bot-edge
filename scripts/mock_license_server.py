# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司
#!/usr/bin/env python3
"""Local mock license server. Same machine re-activate 200; other machine 409."""
from __future__ import annotations

import argparse
import json
import os
import secrets
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import urlparse


class LicenseStore:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._by_key: dict[str, dict[str, Any]] = {}
        self._by_token: dict[str, dict[str, Any]] = {}

    def activate(self, product_key: str, machine_id: str) -> tuple[int, dict[str, Any]]:
        if not product_key or not machine_id:
            return 400, {"error": "product_key and machine_id are required"}
        with self._lock:
            existing = self._by_key.get(product_key)
            if existing and existing["machine_id"] != machine_id:
                return 409, {"error": "product_key already bound to another machine", "code": "machine_mismatch"}
            if existing and existing["machine_id"] == machine_id:
                return 200, dict(existing)
            token = f"tok_{secrets.token_hex(16)}"
            record = {
                "license_token": token,
                "product_key": product_key,
                "machine_id": machine_id,
                "venue_id": f"venue_{secrets.token_hex(4)}",
                "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "product": "Monitor bot Edge",
            }
            self._by_key[product_key] = record
            self._by_token[token] = record
            return 200, dict(record)

    def heartbeat(self, license_token: str, machine_id: str) -> tuple[int, dict[str, Any]]:
        if not license_token or not machine_id:
            return 400, {"error": "license_token and machine_id are required"}
        with self._lock:
            record = self._by_token.get(license_token)
            if record is None:
                return 404, {"error": "unknown license_token"}
            if record["machine_id"] != machine_id:
                return 409, {"error": "license_token bound to another machine", "code": "machine_mismatch"}
            return 200, {"ok": True, "status": "active", "machine_id": machine_id}


def make_handler(store: LicenseStore) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt: str, *args: object) -> None:
            if os.environ.get("MOCK_LICENSE_VERBOSE"):
                super().log_message(fmt, *args)

        def _read_json(self) -> tuple[int, dict[str, Any] | None]:
            length = int(self.headers.get("Content-Length") or 0)
            if length <= 0 or length > 1_000_000:
                return 400, None
            try:
                data = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return 400, None
            return (200, data) if isinstance(data, dict) else (400, None)

        def _send(self, code: int, body: dict[str, Any]) -> None:
            payload = json.dumps(body).encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def do_POST(self) -> None:
            path = urlparse(self.path).path.rstrip("/") or "/"
            status, data = self._read_json()
            if data is None:
                self._send(status, {"error": "invalid JSON body"})
                return
            if path == "/api/edge/activate":
                self._send(*store.activate(str(data.get("product_key") or ""), str(data.get("machine_id") or "")))
                return
            if path == "/api/edge/heartbeat":
                self._send(*store.heartbeat(str(data.get("license_token") or ""), str(data.get("machine_id") or "")))
                return
            self._send(404, {"error": "not found"})

    return Handler


def make_server(host: str = "127.0.0.1", port: int = 8765, store: LicenseStore | None = None):
    store = store or LicenseStore()
    return ThreadingHTTPServer((host, port), make_handler(store)), store


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Mock Monitor bot Edge license server.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    httpd, _ = make_server(args.host, args.port)
    host, port = httpd.server_address[:2]
    print(f"Monitor bot Edge mock license server on http://{host}:{port}")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nstopped")
    finally:
        httpd.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
