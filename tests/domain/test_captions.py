"""Tests for ASS caption rendering, timestamps, and safe margins."""

from smartmech.domain.captions import (
    WordTimestamp,
    format_ass_timestamp,
    generate_ass_content,
)


def test_format_ass_timestamp() -> None:
    assert format_ass_timestamp(0.0) == "0:00:00.00"
    assert format_ass_timestamp(1.25) == "0:00:01.25"
    assert format_ass_timestamp(65.5) == "0:01:05.50"


def test_generate_ass_content_contains_playres_and_safe_margins() -> None:
    words = [
        WordTimestamp(word="Building", start_seconds=0.0, end_seconds=0.5),
        WordTimestamp(word="the", start_seconds=0.5, end_seconds=0.8),
        WordTimestamp(word="future", start_seconds=0.8, end_seconds=1.4),
        WordTimestamp(word="today", start_seconds=1.4, end_seconds=2.0),
    ]

    ass = generate_ass_content(words, play_res_x=1080, play_res_y=1920, safe_margin_bottom=320)
    assert "PlayResX: 1080" in ass
    assert "PlayResY: 1920" in ass
    assert "Dialogue: 0,0:00:00.00" in ass
    assert "Building the future" in ass
