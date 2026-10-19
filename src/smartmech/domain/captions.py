"""Captions, word alignments, and Advanced SubStation Alpha (ASS) models."""

from pydantic import BaseModel, ConfigDict, Field


class WordTimestamp(BaseModel):
    """Word-level alignment timestamp."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    word: str = Field(min_length=1)
    start_seconds: float = Field(ge=0.0)
    end_seconds: float = Field(ge=0.0)

    def duration(self) -> float:
        return max(0.0, self.end_seconds - self.start_seconds)


class SubtitleEvent(BaseModel):
    """Dialogue event for ASS subtitle rendering."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    start_time: str = Field(pattern=r"^\d+:\d{2}:\d{2}\.\d{2}$")
    end_time: str = Field(pattern=r"^\d+:\d{2}:\d{2}\.\d{2}$")
    text: str = Field(min_length=1)


def format_ass_timestamp(seconds: float) -> str:
    """Format floating point seconds into ASS timestamp format H:MM:SS.cc."""
    total_centisecs = round(seconds * 100)
    centisecs = total_centisecs % 100
    total_secs = total_centisecs // 100
    secs = total_secs % 60
    total_mins = total_secs // 60
    mins = total_mins % 60
    hours = total_mins // 60
    return f"{hours}:{mins:02d}:{secs:02d}.{centisecs:02d}"


def generate_ass_content(
    words: list[WordTimestamp],
    play_res_x: int = 1080,
    play_res_y: int = 1920,
    safe_margin_bottom: int = 320,
) -> str:
    """Generate ASS subtitle script with explicit 9:16 safe area and PlayRes."""
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {play_res_x}
PlayResY: {play_res_y}
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Arial,72,&H00FFFFFF,&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,2,100,100,{safe_margin_bottom},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events: list[str] = []
    # Group words into 3-4 word phrases for readability
    chunk_size = 3
    for i in range(0, len(words), chunk_size):
        chunk = words[i : i + chunk_size]
        if not chunk:
            continue
        start_ts = format_ass_timestamp(chunk[0].start_seconds)
        end_ts = format_ass_timestamp(chunk[-1].end_seconds)
        phrase_text = " ".join(w.word for w in chunk)
        events.append(f"Dialogue: 0,{start_ts},{end_ts},Default,,0,0,0,,{phrase_text}")

    return header + "\n".join(events) + "\n"
