"""Fake video generation adapter producing real 1080x1920 MP4 clips via ffmpeg lavfi."""

import asyncio
import subprocess

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.ports.video_gen import VideoGenPort


def _generate_mp4_in_thread(duration_seconds: float, seed: int) -> bytes:
    """Generate a real 1080x1920 30fps h264 video clip with motion via ffmpeg lavfi."""
    hue_val = (seed * 60) % 360
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"testsrc=s=1080x1920:r=30:d={duration_seconds:.2f},hue=h={hue_val}",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-f",
        "mp4",
        "-movflags",
        "frag_keyframe+empty_moov",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    return proc.stdout


class FakeVideoGenAdapter(VideoGenPort):
    """Produces playable 1080x1920 MP4 clips using local FFmpeg lavfi filters."""

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
        identity: AdapterIdentity | None = None,
    ) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=1.0,
            max_duration_seconds=10.0,
            supports_first_frame=True,
            supports_last_frame=True,
            supports_native_audio=False,
        )
        self._identity = identity or AdapterIdentity(
            port="video_gen",
            adapter_name="fake_video_gen",
            model_or_version="lavfi_v1",
            cost_estimate_per_call=0.50,
        )

    @property
    def identity(self) -> AdapterIdentity:
        return self._identity

    @property
    def cost_estimate_per_call(self) -> float:
        return self._identity.cost_estimate_per_call

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    async def generate_transition(
        self,
        from_image: bytes,
        to_image: bytes | None,
        motion_prompt: str,
        duration_seconds: float,
        seed: int,
    ) -> bytes:
        return await asyncio.to_thread(_generate_mp4_in_thread, duration_seconds, seed)
