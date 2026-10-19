"""Contract test execution across all fake adapters."""

from pathlib import Path

import pytest

from smartmech.adapters.fake_aligner import FakeAlignerAdapter
from smartmech.adapters.fake_image_gen import FakeImageGenAdapter
from smartmech.adapters.fake_planner import FakePlannerAdapter
from smartmech.adapters.fake_publisher import FakePublisherAdapter
from smartmech.adapters.fake_speech import FakeSpeechAdapter
from smartmech.adapters.fake_video_gen import FakeVideoGenAdapter
from smartmech.adapters.local_artifact_store import LocalArtifactStoreAdapter
from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from tests.adapters.contract_suite import (
    verify_aligner_contract,
    verify_artifact_store_contract,
    verify_cost_ledger_contract,
    verify_image_gen_contract,
    verify_planner_contract,
    verify_publisher_contract,
    verify_speech_contract,
    verify_video_gen_contract,
)


@pytest.mark.asyncio
async def test_planner_adapter_contract() -> None:
    adapter = FakePlannerAdapter()
    await verify_planner_contract(adapter)


@pytest.mark.asyncio
async def test_image_gen_adapter_contract() -> None:
    adapter = FakeImageGenAdapter()
    await verify_image_gen_contract(adapter)


@pytest.mark.asyncio
async def test_video_gen_adapter_contract() -> None:
    adapter = FakeVideoGenAdapter()
    await verify_video_gen_contract(adapter)


@pytest.mark.asyncio
async def test_speech_adapter_contract() -> None:
    adapter = FakeSpeechAdapter()
    await verify_speech_contract(adapter)


@pytest.mark.asyncio
async def test_aligner_adapter_contract() -> None:
    adapter = FakeAlignerAdapter()
    await verify_aligner_contract(adapter)


@pytest.mark.asyncio
async def test_publisher_adapter_contract() -> None:
    adapter = FakePublisherAdapter()
    await verify_publisher_contract(adapter)


@pytest.mark.asyncio
async def test_artifact_store_adapter_contract(tmp_path: Path) -> None:
    adapter = LocalArtifactStoreAdapter(base_directory=tmp_path / "artifacts")
    await verify_artifact_store_contract(adapter)


@pytest.mark.asyncio
async def test_cost_ledger_adapter_contract() -> None:
    adapter = MemoryCostLedgerAdapter()
    await verify_cost_ledger_contract(adapter)
