# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""Simple IoU tracker for person-like boxes. No appearance / ReID / VL."""

from __future__ import annotations

from dataclasses import dataclass, field


def iou(
    a: tuple[float, float, float, float],
    b: tuple[float, float, float, float],
) -> float:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1, iy1 = max(ax1, bx1), max(ay1, by1)
    ix2, iy2 = min(ax2, bx2), min(ay2, by2)
    inter_w = max(0.0, ix2 - ix1)
    inter_h = max(0.0, iy2 - iy1)
    inter = inter_w * inter_h
    if inter <= 0.0:
        return 0.0
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def box_center(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def box_size(box: tuple[float, float, float, float]) -> tuple[float, float]:
    x1, y1, x2, y2 = box
    return (max(0.0, x2 - x1), max(0.0, y2 - y1))


@dataclass
class Detection:
    box: tuple[float, float, float, float]
    label: str
    confidence: float


@dataclass
class Track:
    track_id: int
    box: tuple[float, float, float, float]
    label: str
    confidence: float
    last_frame: int
    hits: int = 1
    history: list[tuple[int, tuple[float, float, float, float]]] = field(
        default_factory=list
    )

    def record(self, frame_idx: int) -> None:
        self.history.append((frame_idx, self.box))
        if len(self.history) > 240:
            self.history = self.history[-240:]


class IoUTracker:
    def __init__(self, iou_threshold: float = 0.3, max_age: int = 30) -> None:
        self.iou_threshold = iou_threshold
        self.max_age = max_age
        self._next_id = 1
        self._tracks: dict[int, Track] = {}

    @property
    def tracks(self) -> list[Track]:
        return list(self._tracks.values())

    def update(self, detections: list[Detection], frame_idx: int) -> list[Track]:
        track_ids = list(self._tracks.keys())
        assigned_tracks: set[int] = set()
        assigned_dets: set[int] = set()
        pairs: list[tuple[float, int, int]] = []
        for ti, tid in enumerate(track_ids):
            track = self._tracks[tid]
            for di, det in enumerate(detections):
                score = iou(track.box, det.box)
                if score >= self.iou_threshold:
                    pairs.append((score, ti, di))
        pairs.sort(reverse=True)
        for _score, ti, di in pairs:
            tid = track_ids[ti]
            if tid in assigned_tracks or di in assigned_dets:
                continue
            det = detections[di]
            track = self._tracks[tid]
            track.box = det.box
            track.label = det.label
            track.confidence = det.confidence
            track.last_frame = frame_idx
            track.hits += 1
            track.record(frame_idx)
            assigned_tracks.add(tid)
            assigned_dets.add(di)
        for di, det in enumerate(detections):
            if di in assigned_dets:
                continue
            tid = self._next_id
            self._next_id += 1
            track = Track(
                track_id=tid,
                box=det.box,
                label=det.label,
                confidence=det.confidence,
                last_frame=frame_idx,
            )
            track.record(frame_idx)
            self._tracks[tid] = track
        expired = [
            tid
            for tid, track in self._tracks.items()
            if frame_idx - track.last_frame > self.max_age
        ]
        for tid in expired:
            del self._tracks[tid]
        live = [t for t in self._tracks.values() if t.last_frame == frame_idx]
        live.sort(key=lambda t: t.track_id)
        return live
