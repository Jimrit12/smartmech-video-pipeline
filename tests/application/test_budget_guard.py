"""Tests for BudgetGuard application policy."""

import pytest

from smartmech.adapters.memory_cost_ledger import MemoryCostLedgerAdapter
from smartmech.application.budget_guard import BudgetGuard
from smartmech.domain.budget import BudgetConfig, BudgetExceededError, CostRecord


@pytest.mark.asyncio
async def test_budget_guard_allows_spend_within_limits() -> None:
    ledger = MemoryCostLedgerAdapter()
    config = BudgetConfig(per_run_budget=10.0, per_day_budget=50.0)
    guard = BudgetGuard(ledger, config)

    # Pre-check allows call
    await guard.check_budget_before_call(run_id="run-1", estimated_cost=2.0)

    # Record spend
    await guard.record_spend(
        CostRecord(
            port="image_gen", adapter="fake", operation="generate", cost_units=2.0, run_id="run-1"
        )
    )

    run_spend = await ledger.get_run_cost("run-1")
    assert run_spend == 2.0


@pytest.mark.asyncio
async def test_budget_guard_raises_on_per_run_exceeded() -> None:
    ledger = MemoryCostLedgerAdapter()
    config = BudgetConfig(per_run_budget=5.0, per_day_budget=50.0)
    guard = BudgetGuard(ledger, config)

    await guard.record_spend(
        CostRecord(
            port="video_gen", adapter="fake", operation="generate", cost_units=4.5, run_id="run-1"
        )
    )

    # Attempting another operation that would exceed 5.0
    with pytest.raises(BudgetExceededError, match="per-run budget"):
        await guard.check_budget_before_call(run_id="run-1", estimated_cost=1.0)


@pytest.mark.asyncio
async def test_budget_guard_raises_on_per_day_exceeded() -> None:
    ledger = MemoryCostLedgerAdapter()
    config = BudgetConfig(per_run_budget=20.0, per_day_budget=15.0)
    guard = BudgetGuard(ledger, config)

    await guard.record_spend(
        CostRecord(
            port="video_gen", adapter="fake", operation="generate", cost_units=12.0, run_id="run-1"
        )
    )

    # Next run attempts spend that would breach daily 15.0 cap
    with pytest.raises(BudgetExceededError, match="per-day budget"):
        await guard.check_budget_before_call(run_id="run-2", estimated_cost=4.0)
