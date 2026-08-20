# SPDX-License-Identifier: AGPL-3.0-or-later
from monitor_bot_edge.keywords import PHRASE_TO_CLASS, keywords_to_classes, map_phrase, split_keywords

def test_split_mixed_separators():
    assert split_keywords("幼兒、跌倒，攀爬;獨處") == ["幼兒", "跌倒", "攀爬", "獨處"]

def test_unknown_passthrough():
    assert map_phrase("backpack") == "backpack"
    assert keywords_to_classes("幼兒,跌倒,攀爬,backpack") == ["child", "fallen person", "person climbing", "backpack"]

def test_required_zh_mapped():
    for phrase in ("幼兒", "跌倒", "攀爬", "獨處", "聚集"):
        assert PHRASE_TO_CLASS[phrase] != phrase
