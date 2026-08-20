# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""Geometry and time safety rules. No vision-language model.

Operates on IoU-tracked person-like boxes only:
fall, climb, alone, crowd.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from monitor_bot_edge.tracker import Track, box_center, box_size

PERSON_HINTS = (
    "person", "child", "toddler", "kid", "infant", "crowd", "people", "human", "幼兒",
)


def is_person_like(label: str) -> bool:
    text = (label or "").strip().lower()
    if not text:
        return False
    return any(hint in text for hint in PERSON_HINTS)


def _union(boxes: Iterable[tuple[float, float, float, float]]) -> list[float]:
    items = list(boxes)
    if not items:
        return [0.0, 0.0, 0.0, 0.0]
    return [min(b[0] for b in items), min(b[1] for b in items), max(b[2] for b in items), max(b[3] for b in items)]


@dataclass
class RuleEvent:
    time: float
    label: str
    confidence: float
    box: list[float]
    track_id: int | None = None
    source: str = "rule"


class SafetyRules:
    def __init__(
        self,
        *,
        fps: float = 25.0,
        fall_aspect: float = 1.2,
        fall_hold_s: float = 0.4,
        fall_height_ratio: float = 0.55,
        climb_up_ratio: float = 0.35,
        climb_window_s: float = 0.8,
        climb_min_aspect: float = 1.25,
        alone_s: float = 8.0,
        crowd_count: int = 4,
        cooldown_s: float = 3.0,
    ) -> None:
        self.fps = max(float(fps), 1.0)
        self.fall_aspect = fall_aspect
        self.fall_hold_s = fall_hold_s
        self.fall_height_ratio = fall_height_ratio
        self.climb_up_ratio = climb_up_ratio
        self.climb_window_s = climb_window_s
        self.climb_min_aspect = climb_min_aspect
        self.alone_s = alone_s
        self.crowd_count = crowd_count
        self.cooldown_s = cooldown_s
        self._active: dict[tuple[str, str], bool] = {}
        self._last_emit: dict[tuple[str, str], float] = {}
        self._fall_since: dict[int, float | None] = {}
        self._alone_since: float | None = None
        self._crowd_since: float | None = None

    def update(self, tracks: list[Track], frame_idx: int, time_s: float) -> list[RuleEvent]:
        persons = [t for t in tracks if is_person_like(t.label)]
        events: list[RuleEvent] = []
        for track in persons:
            events.extend(self._fall_events(track, time_s))
            events.extend(self._climb_events(track, time_s))
        events.extend(self._alone_events(persons, time_s))
        events.extend(self._crowd_events(persons, time_s))
        return events

    def _maybe(self, key: tuple[str, str], condition: bool, time_s: float, event: RuleEvent) -> list[RuleEvent]:
        if condition:
            already = self._active.get(key, False)
            last = self._last_emit.get(key, -1e18)
            self._active[key] = True
            if not already and (time_s - last) >= self.cooldown_s:
                self._last_emit[key] = time_s
                return [event]
            return []
        self._active[key] = False
        return []

    def _fall_events(self, track: Track, time_s: float) -> list[RuleEvent]:
        _w, h = box_size(track.box)
        aspect = (_w / h) if h > 1.0 else 0.0
        heights = [box_size(b)[1] for _f, b in track.history[-int(self.fps * 2) :] if box_size(b)[1] > 1.0]
        max_h = max(heights) if heights else h
        collapsed = max_h > 1.0 and h <= max_h * self.fall_height_ratio
        lying = aspect >= self.fall_aspect
        now_fall = lying or (collapsed and aspect >= 0.9)
        tid = track.track_id
        if now_fall:
            if self._fall_since.get(tid) is None:
                self._fall_since[tid] = time_s
        else:
            self._fall_since[tid] = None
        started = self._fall_since.get(tid)
        held = started is not None and (time_s - started) >= self.fall_hold_s
        return self._maybe(("fall", str(tid)), held, time_s, RuleEvent(time=time_s, label="fall", confidence=float(track.confidence), box=[float(x) for x in track.box], track_id=tid))

    def _climb_events(self, track: Track, time_s: float) -> list[RuleEvent]:
        window = max(1, int(round(self.climb_window_s * self.fps)))
        hist = track.history[-window:]
        if len(hist) < max(2, window // 2):
            return []
        _w, h = box_size(track.box)
        if h <= 1.0 or (_w > 0 and h / _w < self.climb_min_aspect):
            return []
        y0 = box_center(hist[0][1])[1]
        y1 = box_center(hist[-1][1])[1]
        climbing = (y0 - y1) >= self.climb_up_ratio * h
        return self._maybe(("climb", str(track.track_id)), climbing, time_s, RuleEvent(time=time_s, label="climb", confidence=float(track.confidence), box=[float(x) for x in track.box], track_id=track.track_id))

    def _alone_events(self, persons: list[Track], time_s: float) -> list[RuleEvent]:
        if len(persons) == 1:
            if self._alone_since is None:
                self._alone_since = time_s
        else:
            self._alone_since = None
        held = self._alone_since is not None and (time_s - self._alone_since) >= self.alone_s
        box = [float(x) for x in persons[0].box] if len(persons) == 1 else [0.0, 0.0, 0.0, 0.0]
        conf = float(persons[0].confidence) if len(persons) == 1 else 1.0
        tid = persons[0].track_id if len(persons) == 1 else None
        return self._maybe(("alone", "scene"), held, time_s, RuleEvent(time=time_s, label="alone", confidence=conf, box=box, track_id=tid))

    def _crowd_events(self, persons: list[Track], time_s: float) -> list[RuleEvent]:
        crowded = len(persons) >= self.crowd_count
        if crowded:
            if self._crowd_since is None:
                self._crowd_since = time_s
        else:
            self._crowd_since = None
        box = _union(t.box for t in persons) if persons else [0.0, 0.0, 0.0, 0.0]
        conf = sum(t.confidence for t in persons) / len(persons) if persons else 1.0
        return self._maybe(("crowd", "scene"), crowded, time_s, RuleEvent(time=time_s, label="crowd", confidence=float(conf), box=box, track_id=None))
