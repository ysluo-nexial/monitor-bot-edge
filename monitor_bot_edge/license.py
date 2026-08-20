# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""Local product-key license gate for Monitor bot Edge.

Detection must not load YOLO unless license/license.json contains license_token.
One product key binds to one venue and one machine (enforced by the license server).
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


class LicenseError(RuntimeError):
    """Raised when the local license is missing or has no license_token."""


def repo_root() -> Path:
    """Return the repository root (directory that contains scripts/activate.py)."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "scripts" / "activate.py").exists():
            return parent
        if (parent / "pyproject.toml").exists() and (parent / "monitor_bot_edge").is_dir():
            return parent
    return Path.cwd()


def resolve_license_path(path: str | os.PathLike[str] | None = None) -> Path:
    """Resolve license/license.json, honoring LICENSE_PATH."""
    if path is not None:
        return Path(path)
    env = os.environ.get("LICENSE_PATH")
    if env:
        return Path(env)
    return repo_root() / "license" / "license.json"


def require_license(path: str | os.PathLike[str] | None = None) -> dict[str, Any]:
    """Return the license payload or raise LicenseError.

    Refuses when the file is missing, is not JSON, or lacks a non-empty
    ``license_token``. Call this from every detect entry point *before*
    importing or loading YOLO.
    """
    license_path = resolve_license_path(path)
    if not license_path.is_file():
        raise LicenseError(
            f"No license at {license_path}. Run: python scripts/activate.py"
        )
    try:
        data = json.loads(license_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LicenseError(f"License file is not valid JSON: {license_path}") from exc
    if not isinstance(data, dict):
        raise LicenseError(f"License file must be a JSON object: {license_path}")
    token = data.get("license_token")
    if not isinstance(token, str) or not token.strip():
        raise LicenseError(
            f"License file missing license_token: {license_path}"
        )
    return data
