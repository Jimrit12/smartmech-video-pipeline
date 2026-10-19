"""Fake image generation adapter producing real 1080x1920 PNG frames via ffmpeg lavfi."""

import asyncio
import subprocess

from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import SiteBible
from smartmech.ports.image_gen import ImageGenPort


def _generate_png_in_thread(seed: int) -> bytes:
    """Generate a 1080x1920 solid color frame with seed-derived hue via ffmpeg lavfi."""
    colors = ["#1A365D", "#2B6CB0", "#2C5282", "#1A202C", "#2D3748", "#4A5568"]
    color = colors[seed % len(colors)]
    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"color=c={color}:s=1080x1920:d=0.1",
        "-frames:v",
        "1",
        "-c:v",
        "png",
        "-f",
        "image2pipe",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    return proc.stdout


class FakeImageGenAdapter(ImageGenPort):
    """Generates valid 1080x1920 PNG images using local FFmpeg lavfi filters."""

    def __init__(self, capabilities: AdapterCapabilities | None = None) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=0.0,
            max_duration_seconds=0.0,
            supports_first_frame=True,
            supports_last_frame=True,
            supports_native_audio=False,
        )

    @property
    def capabilities(self) -> AdapterCapabilities:
        return self._capabilities

    async def generate_image(self, prompt: str, site_bible: SiteBible, seed: int) -> bytes:
        # Avoid blocking the asyncio event loop by using asyncio.to_thread
        return await asyncio.to_thread(_generate_png_in_thread, seed)
