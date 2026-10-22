"""Negative integration tests proving QC gates fail on defective synthetic videos."""

import asyncio
import subprocess
from pathlib import Path

import pytest

from smartmech.application.compositor import Compositor
from smartmech.domain.qc import QCGateStatus, QCReport


def _create_synthetic_video_in_thread(cmd: list[str]) -> None:
    subprocess.run(cmd, check=True, capture_output=True)


@pytest.mark.asyncio
async def test_qc_negative_black_frames_fails(tmp_path: Path) -> None:
    """A video containing a black segment must FAIL the BlackFrames gate."""
    video_path = tmp_path / "qc_black_segment.mp4"
    # Create 3-second video: 1s red, 1s black, 1s blue with normal audio
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=red:s=1080x1920:d=1",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1080x1920:d=1",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=1080x1920:d=1",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=3",
        "-filter_complex",
        "[0:v][1:v][2:v]concat=n=3:v=1:a=0[vout];[3:a]loudnorm=I=-14:LRA=7:tp=-1.5[aout]",
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    await asyncio.to_thread(_create_synthetic_video_in_thread, cmd)

    compositor = Compositor()
    metrics = await compositor.probe(str(video_path))
    assert metrics.black_frame_count > 0, "Black segments must be detected"

    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL
    black_gate = next(g for g in report.gates if g.name == "BlackFrames")
    assert black_gate.status == QCGateStatus.FAIL


@pytest.mark.asyncio
async def test_qc_negative_frozen_frames_fails(tmp_path: Path) -> None:
    """A video containing a frozen static segment must FAIL the FrozenFrames gate."""
    video_path = tmp_path / "qc_frozen_segment.mp4"
    # Create 3-second completely static color video with normal audio
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=blue:s=1080x1920:d=3",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=3",
        "-af",
        "loudnorm=I=-14:LRA=7:tp=-1.5",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    await asyncio.to_thread(_create_synthetic_video_in_thread, cmd)

    compositor = Compositor()
    metrics = await compositor.probe(str(video_path))
    assert metrics.frozen_frame_count > 0, "Frozen frames must be detected"

    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL
    frozen_gate = next(g for g in report.gates if g.name == "FrozenFrames")
    assert frozen_gate.status == QCGateStatus.FAIL


@pytest.mark.asyncio
async def test_qc_negative_loudness_fails(tmp_path: Path) -> None:
    """A video with over-loud unnormalized audio must FAIL the Loudness gate."""
    video_path = tmp_path / "qc_overloud.mp4"
    # Create video with boosted audio (+18 dB above unity gain)
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=1080x1920:rate=30:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=2",
        "-af",
        "volume=18dB",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    await asyncio.to_thread(_create_synthetic_video_in_thread, cmd)

    compositor = Compositor()
    metrics = await compositor.probe(str(video_path))
    assert metrics.loudness_lufs > -11.0, (
        f"Expected over-loud audio, got {metrics.loudness_lufs} LUFS"
    )

    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL
    loudness_gate = next(g for g in report.gates if g.name == "Loudness")
    assert loudness_gate.status == QCGateStatus.FAIL


@pytest.mark.asyncio
async def test_qc_negative_landscape_in_portrait_container_fails(tmp_path: Path) -> None:
    """A landscape video inside a portrait container (letterbox) must FAIL the Orientation gate."""
    video_path = tmp_path / "qc_letterbox_landscape.mp4"
    # Create 1080x1920 black canvas with a 1080x500 active landscape video centered in the middle
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        "color=c=black:s=1080x1920:d=2",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=1080x500:rate=30:duration=2",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=1000:duration=2",
        "-filter_complex",
        "[0:v][1:v]overlay=0:710[vout];[2:a]loudnorm=I=-14:LRA=7:tp=-1.5[aout]",
        "-map",
        "[vout]",
        "-map",
        "[aout]",
        "-c:v",
        "libx264",
        "-c:a",
        "aac",
        "-pix_fmt",
        "yuv420p",
        str(video_path),
    ]
    await asyncio.to_thread(_create_synthetic_video_in_thread, cmd)

    compositor = Compositor()
    metrics = await compositor.probe(str(video_path))
    assert not metrics.is_portrait, (
        "Landscape video in portrait container must not be detected as portrait"
    )

    report = QCReport.evaluate(metrics)
    assert report.overall_status == QCGateStatus.FAIL
    orientation_gate = next(g for g in report.gates if g.name == "Orientation")
    assert orientation_gate.status == QCGateStatus.FAIL
