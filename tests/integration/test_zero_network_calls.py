"""Test verifying zero real network calls during pipeline execution."""

import asyncio
import socket
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from unittest.mock import patch

import pytest

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.pipeline_runner import PipelineRunner


class RealNetworkAttemptError(Exception):
    """Raised if an unmocked network connection is attempted."""


@contextmanager
def intercept_network_calls() -> Generator[list[dict[str, object]], None, None]:
    """Context manager intercepting socket.connect, socket.connect_ex, and socket.getaddrinfo.

    Every intercepted attempt is recorded into a shared list and raises RealNetworkAttemptError.
    """
    attempts: list[dict[str, object]] = []
    orig_connect = socket.socket.connect
    orig_socketpair = socket.socketpair

    def forbidden_connect(*args: object, **kwargs: object) -> None:
        attempts.append({"function": "connect", "args": args, "kwargs": kwargs})
        raise RealNetworkAttemptError(f"Forbidden socket.connect attempted: {args} {kwargs}")

    def forbidden_connect_ex(*args: object, **kwargs: object) -> int:
        attempts.append({"function": "connect_ex", "args": args, "kwargs": kwargs})
        raise RealNetworkAttemptError(f"Forbidden socket.connect_ex attempted: {args} {kwargs}")

    def forbidden_getaddrinfo(*args: object, **kwargs: object) -> list[tuple[object, ...]]:
        attempts.append({"function": "getaddrinfo", "args": args, "kwargs": kwargs})
        raise RealNetworkAttemptError(f"Forbidden socket.getaddrinfo attempted: {args} {kwargs}")

    def safe_socketpair(
        family: int = socket.AF_INET, type: int = socket.SOCK_STREAM, proto: int = 0
    ) -> tuple[socket.socket, socket.socket]:
        socket.socket.connect = orig_connect  # type: ignore[method-assign]
        try:
            return orig_socketpair(family, type, proto)
        finally:
            socket.socket.connect = forbidden_connect  # type: ignore[method-assign]

    with (
        patch.object(socket.socket, "connect", side_effect=forbidden_connect),
        patch.object(socket.socket, "connect_ex", side_effect=forbidden_connect_ex),
        patch.object(socket, "getaddrinfo", side_effect=forbidden_getaddrinfo),
        patch.object(socket, "socketpair", side_effect=safe_socketpair),
    ):
        yield attempts


@pytest.mark.asyncio
async def test_zero_real_network_calls_during_pipeline(tmp_path: Path) -> None:
    output_dir = tmp_path / "offline_output"
    store = LocalArtifactStoreAdapter(base_directory=output_dir / "artifacts")
    ledger = MemoryCostLedgerAdapter()

    runner = PipelineRunner(
        planner=FakePlannerAdapter(),
        image_gen=FakeImageGenAdapter(),
        video_gen=FakeVideoGenAdapter(),
        speech=FakeSpeechAdapter(),
        aligner=FakeAlignerAdapter(),
        publisher=FakePublisherAdapter(),
        artifact_store=store,
        cost_ledger=ledger,
        dbos_sqlite_path=str(tmp_path / "offline_dbos.sqlite"),
        output_directory=str(output_dir),
    )

    # Intercept socket connect, connect_ex, and getaddrinfo during pipeline execution
    with intercept_network_calls() as recorded_attempts:
        report = await runner.execute_run(
            run_id="run_offline_verified", prompt="Offline Skyscraper", seed=99
        )

    assert report["status"] == "PASS"
    assert recorded_attempts == [], (
        f"Zero network calls expected, but attempts were recorded: {recorded_attempts}"
    )
    video_exists = await asyncio.to_thread(Path(report["video_path"]).exists)
    assert video_exists


def test_network_guard_canary_trips_on_connection_attempt() -> None:
    """Canary test proving that intercept_network_calls records attempts and raises RealNetworkAttemptError."""
    with intercept_network_calls() as recorded_attempts:
        # Test 1: getaddrinfo attempt
        with pytest.raises(RealNetworkAttemptError):
            socket.getaddrinfo("127.0.0.1", 80)
        assert len(recorded_attempts) == 1
        assert recorded_attempts[0]["function"] == "getaddrinfo"

        # Test 2: connect attempt
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            with pytest.raises(RealNetworkAttemptError):
                s.connect(("127.0.0.1", 65432))
            assert len(recorded_attempts) == 2
            assert recorded_attempts[1]["function"] == "connect"

            # Test 3: connect_ex attempt
            with pytest.raises(RealNetworkAttemptError):
                s.connect_ex(("127.0.0.1", 65432))
            assert len(recorded_attempts) == 3
            assert recorded_attempts[2]["function"] == "connect_ex"

            # Test 4: Swallowed exception still records attempt
            try:
                s.connect(("127.0.0.1", 65432))
            except Exception:
                pass
            assert len(recorded_attempts) == 4
            assert recorded_attempts[3]["function"] == "connect"
        finally:
            s.close()
