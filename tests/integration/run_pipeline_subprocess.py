"""Subprocess helper for kill-and-resume integration test."""

import argparse
import asyncio
from pathlib import Path

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.pipeline_runner import PipelineRunner
from smartmech.domain.autonomy import PublishMetadata
from smartmech.domain.captions import WordTimestamp
from smartmech.domain.concept import Plan, SiteBible


def _append_log(log_path: str, message: str) -> None:
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(message + "\n")


def _write_signal(signal_path: str, message: str) -> None:
    with open(signal_path, "w", encoding="utf-8") as f:
        f.write(message)


class LoggingFakePlannerAdapter(FakePlannerAdapter):
    def __init__(self, log_file: Path) -> None:
        super().__init__()
        self.log_file = log_file

    async def plan(self, prompt: str, seed: int) -> Plan:
        await asyncio.to_thread(_append_log, str(self.log_file), f"planner:plan:{prompt}:{seed}")
        return await super().plan(prompt, seed)


class LoggingFakeImageGenAdapter(FakeImageGenAdapter):
    def __init__(self, log_file: Path) -> None:
        super().__init__()
        self.log_file = log_file

    async def generate_image(self, prompt: str, site_bible: SiteBible, seed: int) -> bytes:
        await asyncio.to_thread(
            _append_log, str(self.log_file), f"image_gen:generate_image:{prompt[:20]}:{seed}"
        )
        return await super().generate_image(prompt, site_bible, seed)


class LoggingFakeVideoGenAdapter(FakeVideoGenAdapter):
    def __init__(
        self,
        log_file: Path,
        signal_file: Path | None = None,
        block_on_first_clip: bool = False,
        raise_on_first_clip: bool = False,
    ) -> None:
        super().__init__()
        self.log_file = log_file
        self.signal_file = signal_file
        self.block_on_first_clip = block_on_first_clip
        self.raise_on_first_clip = raise_on_first_clip

    async def generate_transition(
        self,
        from_image: bytes,
        to_image: bytes | None,
        motion_prompt: str,
        duration_seconds: float,
        seed: int,
    ) -> bytes:
        if self.signal_file is not None:
            await asyncio.to_thread(_write_signal, str(self.signal_file), "ready_to_kill")
        if self.block_on_first_clip:
            await asyncio.Event().wait()
        if self.raise_on_first_clip:
            raise KeyboardInterrupt("Simulated in-process crash mid-run after keyframes")

        await asyncio.to_thread(
            _append_log,
            str(self.log_file),
            f"video_gen:generate_transition:{motion_prompt[:20]}:{duration_seconds}:{seed}",
        )
        return await super().generate_transition(
            from_image, to_image, motion_prompt, duration_seconds, seed
        )


class LoggingFakeSpeechAdapter(FakeSpeechAdapter):
    def __init__(self, log_file: Path) -> None:
        super().__init__()
        self.log_file = log_file

    async def generate_speech(self, text: str, voice: str | None = None) -> bytes:
        await asyncio.to_thread(
            _append_log, str(self.log_file), f"speech:generate_speech:{text[:20]}"
        )
        return await super().generate_speech(text, voice)


class LoggingFakeAlignerAdapter(FakeAlignerAdapter):
    def __init__(self, log_file: Path) -> None:
        super().__init__()
        self.log_file = log_file

    async def align(self, audio_bytes: bytes, transcript: str) -> list[WordTimestamp]:
        await asyncio.to_thread(_append_log, str(self.log_file), f"aligner:align:{transcript[:20]}")
        return await super().align(audio_bytes, transcript)


class LoggingFakePublisherAdapter(FakePublisherAdapter):
    def __init__(self, log_file: Path) -> None:
        super().__init__()
        self.log_file = log_file

    async def publish(self, video_path: str, metadata: PublishMetadata) -> str:
        await asyncio.to_thread(
            _append_log, str(self.log_file), f"publisher:publish:{metadata.title}"
        )
        return await super().publish(video_path, metadata)


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-id", required=True)
    parser.add_argument("--dbos-sqlite", required=True)
    parser.add_argument("--artifacts-dir", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--call-log", required=True)
    parser.add_argument("--signal-file", default=None)
    parser.add_argument("--block-on-first-clip", action="store_true")
    args = parser.parse_args()

    call_log = Path(args.call_log)
    signal_file = Path(args.signal_file) if args.signal_file else None

    store = LocalArtifactStoreAdapter(base_directory=Path(args.artifacts_dir))
    ledger = MemoryCostLedgerAdapter()

    runner = PipelineRunner(
        planner=LoggingFakePlannerAdapter(call_log),
        image_gen=LoggingFakeImageGenAdapter(call_log),
        video_gen=LoggingFakeVideoGenAdapter(
            call_log, signal_file=signal_file, block_on_first_clip=args.block_on_first_clip
        ),
        speech=LoggingFakeSpeechAdapter(call_log),
        aligner=LoggingFakeAlignerAdapter(call_log),
        publisher=LoggingFakePublisherAdapter(call_log),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=args.dbos_sqlite,
        output_directory=args.output_dir,
    )

    await runner.execute_run(run_id=args.run_id, prompt="Modern Skyscraper Timelapse", seed=42)


if __name__ == "__main__":
    asyncio.run(main())
