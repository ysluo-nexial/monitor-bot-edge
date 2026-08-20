# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2026 Nexial Technology LTD. / 朔域科技有限公司

"""Open-vocabulary keyword split and Traditional Chinese phrase mapping.

Separators: ideographic comma (、), full-width comma (，), ASCII comma,
ASCII semicolon, and full-width semicolon (；).

This is not a closed whitelist. Unknown phrases pass through unchanged
and are sent to YOLO-World as class prompts.
"""

from __future__ import annotations

import re

_SPLIT = re.compile(r"[、，,;；]+")

PHRASE_TO_CLASS: dict[str, str] = {
    "幼兒": "child",
    "跌倒": "fallen person",
    "攀爬": "person climbing",
    "獨處": "person",
    "聚集": "crowd",
}


def split_keywords(text: str) -> list[str]:
    if text is None:
        return []
    parts: list[str] = []
    for raw in _SPLIT.split(str(text)):
        phrase = raw.strip()
        if phrase:
            parts.append(phrase)
    return parts


def map_phrase(phrase: str) -> str:
    key = phrase.strip()
    return PHRASE_TO_CLASS.get(key, key)


def keywords_to_classes(text: str) -> list[str]:
    classes: list[str] = []
    seen: set[str] = set()
    for phrase in split_keywords(text):
        mapped = map_phrase(phrase)
        if mapped not in seen:
            seen.add(mapped)
            classes.append(mapped)
    return classes
