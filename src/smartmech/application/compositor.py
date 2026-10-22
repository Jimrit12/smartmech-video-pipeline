"""Compositor service executing two-pass loudness normalisation and ffmpeg QC measurement."""

import asyncio
import json
import re
import subprocess
from pathlib import Path

from smartmech.domain.filtergraph import FiltergraphSpec
from smartmech.domain.qc import QCMetrics


class CompositorError(Exception):
    """Raised when FFmpeg encoding or probing fails."""


def _run_ffmpeg_in_thread(cmd: list[str]) -> None:
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise CompositorError(f"FFmpeg encoding failed (exit {proc.returncode}):\n{proc.stderr}")


def _measure_loudnorm_pass1_in_thread(audio_path_str: str, target_lufs: float) -> dict[str, float]:
    """Run pass 1 of EBU R128 loudnorm to measure audio statistics for two-pass normalization."""
    resolved_path = str(Path(audio_path_str).resolve())
    cmd = [
        "ffmpeg",
        "-hide_banner",
        "-i",
        resolved_path,
        "-af",
        f"loudnorm=I={target_lufs:.1f}:LRA=7:tp=-1.5:print_format=json",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    stderr = proc.stderr
    json_start = stderr.rfind("{")
    json_end = stderr.rfind("}")
    if json_start != -1 and json_end != -1 and json_end > json_start:
        json_str = stderr[json_start : json_end + 1]
        try:
            parsed = json.loads(json_str)
            return {
                "measured_i": float(parsed["input_i"]),
                "measured_tp": float(parsed["input_tp"]),
                "measured_lra": float(parsed["input_lra"]),
                "measured_thresh": float(parsed["input_thresh"]),
                "target_offset": float(parsed["target_offset"]),
            }
        except (KeyError, ValueError, json.JSONDecodeError):
            pass
    return {}


def _probe_video_in_thread(video_path_str: str) -> QCMetrics:
    """Extract technical metrics from output video using ffprobe and ffmpeg filters."""
    resolved_path = str(Path(video_path_str).resolve())
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "stream=width,height,r_frame_rate,duration,codec_type",
        "-show_entries",
        "format=duration",
        "-of",
        "json",
        resolved_path,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if proc.returncode != 0:
        raise CompositorError(f"FFprobe inspection failed (exit {proc.returncode}):\n{proc.stderr}")

    data = json.loads(proc.stdout)
    streams = data.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    if not video_stream:
        raise CompositorError("No video stream found in encoded output")

    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    width = int(video_stream["width"])
    height = int(video_stream["height"])

    # Parse fps from r_frame_rate e.g. "30/1" or "30000/1001"
    fps_parts = video_stream.get("r_frame_rate", "30/1").split("/")
    fps = float(fps_parts[0]) / float(fps_parts[1]) if len(fps_parts) == 2 else 30.0

    # Format duration
    format_dur = data.get("format", {}).get("duration")
    video_duration = float(video_stream.get("duration") or format_dur or 0.0)
    audio_duration = (
        float(audio_stream.get("duration") or format_dur or 0.0) if audio_stream else 0.0
    )
    av_duration_delta = abs(video_duration - audio_duration)

    # Measure ebur128, blackdetect, freezedetect, cropdetect in one pass
    filter_args: list[str] = []
    if audio_stream:
        filter_args.extend(["-af", "ebur128"])
    filter_args.extend(
        [
            "-vf",
            "blackdetect=d=0.1:pic_th=0.98,freezedetect=n=0.003:d=1.0,cropdetect=24:16:0",
            "-f",
            "null",
            "-",
        ]
    )

    cmd_ffmpeg = ["ffmpeg", "-hide_banner", "-i", resolved_path, *filter_args]
    proc_measure = subprocess.run(cmd_ffmpeg, capture_output=True, text=True, check=False)
    stderr = proc_measure.stderr

    # Parse ebur128 integrated loudness
    loudness_match = re.search(r"Integrated loudness:\s+I:\s+([-\d.]+)\s+LUFS", stderr)
    if loudness_match:
        loudness_lufs = float(loudness_match.group(1))
    else:
        loudness_lufs = -70.0

    # Parse black frames (count of black segments detected)
    black_matches = re.findall(r"black_start:\s*([-\d.]+)", stderr)
    black_frame_count = len(black_matches)

    # Parse frozen frames (count of freeze segments detected)
    freeze_matches = re.findall(r"freeze_start:\s*([-\d.]+)", stderr)
    frozen_frame_count = len(freeze_matches)

    # Parse cropdetect to detect landscape inside portrait container
    crops = re.findall(r"crop=(\d+):(\d+):", stderr)
    if crops:
        w_crop, h_crop = int(crops[-1][0]), int(crops[-1][1])
        is_active_landscape = w_crop > h_crop
        is_portrait = (height > width) and not is_active_landscape
    else:
        is_portrait = height > width

    return QCMetrics(
        width=width,
        height=height,
        fps=fps,
        duration_seconds=video_duration,
        loudness_lufs=loudness_lufs,
        av_duration_delta_seconds=av_duration_delta,
        black_frame_count=black_frame_count,
        frozen_frame_count=frozen_frame_count,
        is_portrait=is_portrait,
    )


def _check_file_exists_in_thread(path_str: str) -> bool:
    return Path(path_str).exists()


class Compositor:
    """Executes two-pass FFmpeg filtergraph and probes resulting media."""

    async def render(self, spec: FiltergraphSpec) -> QCMetrics:
        """Execute two-pass FFmpeg render and inspect results with ffprobe."""
        # Pass 1: Measure loudnorm statistics if not already provided
        if spec.measured_i is None:
            stats = await asyncio.to_thread(
                _measure_loudnorm_pass1_in_thread, spec.audio_path, spec.target_lufs
            )
            if stats:
                spec = spec.model_copy(update=stats)

        # Pass 2: Execute render with measured stats
        cmd = spec.build_command()
        await asyncio.to_thread(_run_ffmpeg_in_thread, cmd)

        exists = await asyncio.to_thread(_check_file_exists_in_thread, spec.output_path)
        if not exists:
            raise CompositorError(f"Rendered file does not exist at {spec.output_path}")

        return await asyncio.to_thread(_probe_video_in_thread, spec.output_path)

    async def probe(self, video_path: str) -> QCMetrics:
        """Inspect and measure technical QC metrics from a video file."""
        exists = await asyncio.to_thread(_check_file_exists_in_thread, video_path)
        if not exists:
            raise CompositorError(f"Video file does not exist at {video_path}")
        return await asyncio.to_thread(_probe_video_in_thread, video_path)
