# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""YOLO-World video detect for Monitor bot Edge.

License is checked *before* YOLO is imported or loaded.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, TextIO

from monitor_bot_edge.keywords import keywords_to_classes
from monitor_bot_edge.license import require_license
from monitor_bot_edge.rules import RuleEvent, SafetyRules
from monitor_bot_edge.tracker import Detection, IoUTracker, Track

DEFAULT_WEIGHTS = "yolov8s-world.pt"
_COLORS = {"fall": (0, 0, 255), "climb": (0, 140, 255), "alone": (255, 0, 255), "crowd": (0, 255, 255)}
_DEFAULT_COLOR = (40, 200, 40)


@dataclass
class Event:
    time: float
    label: str
    confidence: float
    box: list[float]
    track_id: int | None = None
    source: str = "yolo"

    def to_record(self) -> dict[str, Any]:
        record = {
            "time": round(self.time, 3),
            "label": self.label,
            "confidence": round(self.confidence, 4),
            "box": [round(float(v), 1) for v in self.box],
        }
        if self.track_id is not None:
            record["track_id"] = self.track_id
        if self.source:
            record["source"] = self.source
        return record


def resolve_weights(weights: str | os.PathLike[str] | None = None) -> str:
    if weights:
        return str(weights)
    return os.environ.get("YOLO_WEIGHTS") or DEFAULT_WEIGHTS


def _load_yolo(weights: str, classes: list[str]) -> Any:
    from ultralytics import YOLOWorld
    model = YOLOWorld(weights)
    if classes:
        model.set_classes(classes)
    return model


def _parse_result(result: Any) -> list[Detection]:
    detections: list[Detection] = []
    boxes = getattr(result, "boxes", None)
    if boxes is None:
        return detections
    names = getattr(result, "names", {}) or {}
    xyxy = boxes.xyxy
    confs = boxes.conf
    clss = boxes.cls
    for i in range(len(xyxy)):
        row = xyxy[i]
        box = (float(row[0]), float(row[1]), float(row[2]), float(row[3]))
        cls_i = int(clss[i]) if clss is not None else 0
        label = names.get(cls_i, str(cls_i)) if isinstance(names, dict) else str(cls_i)
        conf = float(confs[i]) if confs is not None else 0.0
        detections.append(Detection(box=box, label=str(label), confidence=conf))
    return detections


def _color_for(label: str) -> tuple[int, int, int]:
    return _COLORS.get(label.lower(), _DEFAULT_COLOR)


def _draw(frame: Any, tracks: Iterable[Track], rules: Iterable[RuleEvent], cv2: Any) -> None:
    for track in tracks:
        x1, y1, x2, y2 = (int(v) for v in track.box)
        color = _color_for(track.label)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
        cv2.putText(frame, f"{track.label} {track.confidence:.2f} #{track.track_id}", (x1, max(16, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    for event in rules:
        x1, y1, x2, y2 = (int(v) for v in event.box)
        color = _color_for(event.label)
        cv2.rectangle(frame, (x1, y1), (x2, y2), color, 3)
        cv2.putText(frame, event.label.upper(), (x1, min(frame.shape[0] - 8, y2 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2, cv2.LINE_AA)


def _write_event(fh: TextIO, event: Event | RuleEvent) -> None:
    if isinstance(event, RuleEvent):
        rec = Event(time=event.time, label=event.label, confidence=event.confidence, box=list(event.box), track_id=event.track_id, source=event.source).to_record()
    else:
        rec = event.to_record()
    fh.write(json.dumps(rec, ensure_ascii=False) + "\n")


def run_detect(
    *,
    video: str | os.PathLike[str],
    keywords: str,
    output_dir: str | os.PathLike[str] = "outputs",
    weights: str | os.PathLike[str] | None = None,
    conf: float = 0.25,
    license_path: str | os.PathLike[str] | None = None,
    fall_hold_s: float = 0.4,
    climb_window_s: float = 0.8,
    alone_s: float = 8.0,
    crowd_count: int = 4,
) -> tuple[Path, Path]:
    require_license(license_path)
    video_path = Path(video)
    if not video_path.is_file():
        raise FileNotFoundError(f"Video not found: {video_path}")
    classes = keywords_to_classes(keywords)
    if not classes:
        raise ValueError("No keywords after split; pass --keywords e.g. '幼兒,跌倒,攀爬'")
    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = video_path.stem
    mp4_path = out_dir / f"{stem}.annotated.mp4"
    jsonl_path = out_dir / f"{stem}.events.jsonl"
    model = _load_yolo(resolve_weights(weights), classes)
    import cv2
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise RuntimeError(f"Could not open video: {video_path}")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0) or 25.0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    writer = cv2.VideoWriter(str(mp4_path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        cap.release()
        raise RuntimeError(f"Could not open writer: {mp4_path}")
    tracker = IoUTracker()
    rules = SafetyRules(fps=fps, fall_hold_s=fall_hold_s, climb_window_s=climb_window_s, alone_s=alone_s, crowd_count=crowd_count)
    frame_idx = 0
    try:
        with jsonl_path.open("w", encoding="utf-8") as ev_fh:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                time_s = frame_idx / fps
                detections: list[Detection] = []
                for result in model.predict(source=frame, conf=conf, verbose=False):
                    detections.extend(_parse_result(result))
                tracks = tracker.update(detections, frame_idx)
                rule_events = rules.update(tracks, frame_idx, time_s)
                for track in tracks:
                    _write_event(ev_fh, Event(time=time_s, label=track.label, confidence=track.confidence, box=list(track.box), track_id=track.track_id, source="yolo"))
                for rule_event in rule_events:
                    _write_event(ev_fh, rule_event)
                _draw(frame, tracks, rule_events, cv2)
                writer.write(frame)
                frame_idx += 1
    finally:
        cap.release()
        writer.release()
    return mp4_path, jsonl_path
