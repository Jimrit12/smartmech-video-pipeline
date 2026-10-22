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


def test_ffmpeg_filtergraph_command_with_two_pass_loudnorm() -> None:
    spec = FiltergraphSpec(
        clip_paths=["clips/clip_0.mp4"],
        clip_durations=[7.0],
        audio_path="audio/voiceover.wav",
        ass_path="subtitles/captions.ass",
        output_path="output/final.mp4",
        measured_i=-21.5,
        measured_tp=-2.1,
        measured_lra=6.2,
        measured_thresh=-32.0,
        target_offset=0.2,
    )
    cmd = spec.build_command()
    cmd_str = " ".join(cmd)
    assert (
        "measured_I=-21.50:measured_TP=-2.10:measured_LRA=6.20:measured_thresh=-32.00:offset=0.20:linear=true"
        in cmd_str
    )
