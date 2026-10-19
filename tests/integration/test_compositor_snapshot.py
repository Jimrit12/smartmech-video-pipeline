"""Snapshot test for single-encode FFmpeg filtergraph command generation."""

from syrupy.assertion import SnapshotAssertion

from smartmech.domain.filtergraph import FiltergraphSpec
from smartmech.domain.strategy import TailTrimPolicy


def test_ffmpeg_filtergraph_command_snapshot(snapshot: SnapshotAssertion) -> None:
    spec = FiltergraphSpec(
        clip_paths=[
            "clips/clip_0.mp4",
            "clips/clip_1.mp4",
            "clips/clip_2.mp4",
            "clips/clip_3.mp4",
            "clips/clip_4.mp4",
        ],
        clip_durations=[7.0, 7.0, 7.0, 7.0, 7.0],
        audio_path="audio/voiceover.wav",
        ass_path="subtitles/captions.ass",
        output_path="output/final.mp4",
        tail_trim_policy=TailTrimPolicy(trim_fraction=0.125),
    )
    cmd = spec.build_command()
    # Normalize command line as joined string for readable snapshot
    cmd_str = " ".join(cmd)
    assert cmd_str == snapshot
