"""Tests asserting that budget spend and variation history survive process restarts."""

import subprocess
import sys
from pathlib import Path

import pytest

from smartmech.adapters.sqlite_cost_ledger import SQLiteCostLedgerAdapter
from smartmech.application.budget_guard import BudgetGuard
from smartmech.application.variation import ConceptTooSimilarError, VariationMemory
from smartmech.domain.budget import BudgetConfig, BudgetExceededError, CostRecord
from smartmech.domain.concept import Concept


def test_process_restart_survival_via_subprocess(tmp_path: Path) -> None:
    """Assert spend and variation history survive real OS process termination and restart."""
    helper_script = Path(__file__).parent / "run_process_restart_helper.py"

    # Step 1: Run in first process, record spend & concept, exit cleanly
    proc1 = subprocess.run(
        [sys.executable, str(helper_script), "--db-dir", str(tmp_path), "--step", "step1"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc1.returncode == 0, f"Process 1 failed: {proc1.stderr}\n{proc1.stdout}"
    assert "STEP1_OK" in proc1.stdout

    # Step 2: Spawn completely new process pointing to same SQLite databases
    proc2 = subprocess.run(
        [sys.executable, str(helper_script), "--db-dir", str(tmp_path), "--step", "step2"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc2.returncode == 0, f"Process 2 failed: {proc2.stderr}\n{proc2.stdout}"
    assert "STEP2_OK" in proc2.stdout


@pytest.mark.asyncio
async def test_process_restart_survival_in_process(tmp_path: Path) -> None:
    """Assert spend and variation history survive instance teardown and reconstruction."""
    ledger_db = tmp_path / "ledger.db"
    variation_db = tmp_path / "variation.db"

    # Session 1: Record spend and concept
    ledger1 = SQLiteCostLedgerAdapter(db_path=ledger_db)
    vm1 = VariationMemory(db_path=variation_db)

    await ledger1.record_cost(
        CostRecord(
            port="speech",
            adapter="fake",
            operation="synthesize",
            cost_units=30.0,
            run_id="run-session-1",
        )
    )
    vm1.check_and_record(
        Concept(
            title="Floating Solar Archipelago",
            premise="Assembling offshore photovoltaic pontoons on a Norwegian fjord",
            building_type="Energy",
        )
    )

    # Discard Session 1 objects completely
    del ledger1
    del vm1

    # Session 2: Fresh instances connecting to the persistent SQLite files
    ledger2 = SQLiteCostLedgerAdapter(db_path=ledger_db)
    vm2 = VariationMemory(db_path=variation_db)

    # Assert prior spend is retained
    assert await ledger2.get_daily_cost() == 30.0
    assert await ledger2.get_run_cost("run-session-1") == 30.0

    # Assert daily budget guard stops excess spend
    guard = BudgetGuard(ledger2, BudgetConfig(per_run_budget=25.0, per_day_budget=50.0))
    with pytest.raises(BudgetExceededError, match="per-day budget"):
        await guard.check_budget_before_call("run-session-2", estimated_cost=25.0)

    # Assert variation memory trips on duplicate concept
    with pytest.raises(ConceptTooSimilarError, match="too similar"):
        vm2.check_and_record(
            Concept(
                title="Floating Solar Archipelago",
                premise="Assembling offshore photovoltaic pontoons on a Norwegian fjord",
                building_type="Energy",
            )
        )

    # Assert novel concept is permitted and recorded
    vm2.check_and_record(
        Concept(
            title="Hyperloop Tube Segment",
            premise="Welding vacuum transit tubes across the Nevada desert salt flats",
            building_type="Transport",
        )
    )
    assert len(vm2.history()) == 2
