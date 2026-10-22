"""Fake forced-aligner adapter distributing transcript words into timestamps."""

import re

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.captions import WordTimestamp
from smartmech.ports.aligner import AlignerPort


class FakeAlignerAdapter(AlignerPort):
    """Produces deterministic word timestamps evenly paced across audio duration."""

    def __init__(
        self,
        capabilities: AdapterCapabilities | None = None,
        identity: AdapterIdentity | None = None,
    ) -> None:
        self._capabilities = capabilities or AdapterCapabilities(
            aspect_ratios=["9:16"],
            min_duration_seconds=5.0,
            max_duration_seconds=60.0,
            supports_first_frame=False,
            supports_last_frame=False,
            supports_native_audio=True,
        )
        self._identity = identity or AdapterIdentity(
            port="aligner",
            adapter_name="fake_aligner",
            model_or_version="stub_v1",
            cost_estimate_per_call=0.0,
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

    async def align(self, audio_bytes: bytes, transcript: str) -> list[WordTimestamp]:
        words = re.findall(r"\b\w+\b", transcript)
        if not words:
            return []

        # Target 30-35s duration
        total_duration = 34.0
        word_duration = total_duration / len(words)

        timestamps: list[WordTimestamp] = []
        for i, word in enumerate(words):
            start = i * word_duration
            end = (i + 1) * word_duration
            timestamps.append(
                WordTimestamp(
                    word=word,
                    start_seconds=round(start, 2),
                    end_seconds=round(end, 2),
                )
            )

        return timestamps
