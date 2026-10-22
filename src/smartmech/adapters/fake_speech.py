"""Fake speech generation adapter producing real playable WAV audio via ffmpeg lavfi."""

import asyncio
import subprocess

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.ports.speech import SpeechPort


def _generate_wav_in_thread(text: str) -> bytes:
    """Generate audio tuned to the narrative duration (30-36s) using ffmpeg lavfi."""
    _ = text
    # Target 30.0 - 40.0 second pacing aligned with composite video duration (~30.6s)
    duration = 30.625

    cmd = [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-i",
        f"sine=frequency=320:beep_factor=1.2:d={duration:.2f}",
        "-af",
        "volume=0.3,loudnorm=I=-14:LRA=7:tp=-1.5",
        "-c:a",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        "-f",
        "wav",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, check=True)
    return proc.stdout


class FakeSpeechAdapter(SpeechPort):
    """Produces playable WAV voiceover audio using local FFmpeg lavfi filters."""

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
        identity: AdapterIdentity | None = None,
    ) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=10.0,
            max_duration_seconds=60.0,
            supports_first_frame=False,
            supports_last_frame=False,
            supports_native_audio=True,
        )
        self._identity = identity or AdapterIdentity(
            port="speech",
            adapter_name="fake_speech",
            model_or_version="lavfi_v1",
            cost_estimate_per_call=0.20,
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

    async def generate_speech(self, text: str, voice: str | None = None) -> bytes:
        return await asyncio.to_thread(_generate_wav_in_thread, text)
