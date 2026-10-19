"""Spike test proving syrupy snapshot assertion capability."""

from syrupy.assertion import SnapshotAssertion


def test_syrupy_snapshot_assertion(snapshot: SnapshotAssertion) -> None:
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        "input.mp4",
        "-vf",
        "subtitles=subs.ass",
        "-c:v",
        "libx264",
        "output.mp4",
    ]
    # Verify snapshot match
    assert " ".join(ffmpeg_cmd) == snapshot
