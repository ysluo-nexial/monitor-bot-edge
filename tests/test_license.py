# SPDX-License-Identifier: AGPL-3.0-or-later
import json
from pathlib import Path
import pytest
from monitor_bot_edge.detect import run_detect
from monitor_bot_edge.license import LicenseError, require_license

def test_require_license_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LICENSE_PATH", str(tmp_path / "missing.json"))
    with pytest.raises(LicenseError, match="No license"):
        require_license()

def test_require_license_present(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    path = tmp_path / "license.json"
    path.write_text(json.dumps({"license_token": "tok_ok"}), encoding="utf-8")
    monkeypatch.setenv("LICENSE_PATH", str(path))
    assert require_license()["license_token"] == "tok_ok"

def test_detect_refuses_yolo_without_license(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("LICENSE_PATH", str(tmp_path / "missing.json"))
    loaded = []
    monkeypatch.setattr("monitor_bot_edge.detect._load_yolo", lambda w, c: loaded.append(w))
    with pytest.raises(LicenseError):
        run_detect(video=tmp_path / "none.mp4", keywords="幼兒")
    assert loaded == []
