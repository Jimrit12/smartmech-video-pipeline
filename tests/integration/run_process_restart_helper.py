"""Helper subprocess script testing SQLite persistence across real process restart."""

import argparse
import asyncio
import sys
from pathlib import Path

from smartmech.adapters.sqlite_cost_ledger import SQLiteCostLedgerAdapter
from smartmech.application.budget_guard import BudgetGuard
from smartmech.application.variation import ConceptTooSimilarError, VariationMemory
from smartmech.domain.budget import BudgetConfig, BudgetExceededError, CostRecord
from smartmech.domain.concept import Concept


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-dir", required=True)
    parser.add_argument("--step", required=True, choices=["step1", "step2"])
    args = parser.parse_args()

    db_dir = Path(args.db_dir)
    ledger_db = db_dir / "ledger.db"
    variation_db = db_dir / "variation.db"

    ledger = SQLiteCostLedgerAdapter(db_path=ledger_db)
    vm = VariationMemory(db_path=variation_db)

    if args.step == "step1":
        # Record initial spend
        await ledger.record_cost(
            CostRecord(
                port="video_gen",
                adapter="fake",
                operation="generate_clips",
                cost_units=35.0,
                run_id="run-proc-1",
            )
        )
        # Record initial concept
        vm.check_and_record(
            Concept(
                title="Titan Modular Skyscraper",
                premise="High-rise construction using robotic tower cranes in Shinjuku",
                building_type="Skyscraper",
            )
        )
        print("STEP1_OK")
        sys.exit(0)

    elif args.step == "step2":
        # Verify spend survived process restart
        daily_cost = await ledger.get_daily_cost()
        if daily_cost != 35.0:
            print(f"FAILED: Expected 35.0 daily cost, got {daily_cost}", file=sys.stderr)
            sys.exit(1)

        run_cost = await ledger.get_run_cost("run-proc-1")
        if run_cost != 35.0:
            print(f"FAILED: Expected 35.0 run cost, got {run_cost}", file=sys.stderr)
            sys.exit(1)

        # Verify daily budget guard trips due to persisted prior spend
        guard = BudgetGuard(ledger, BudgetConfig(per_run_budget=20.0, per_day_budget=50.0))
        try:
            await guard.check_budget_before_call("run-proc-2", estimated_cost=20.0)
            print("FAILED: BudgetExceededError was not raised", file=sys.stderr)
            sys.exit(1)
        except BudgetExceededError:
            pass

        # Verify variation memory rejects similar concept due to persisted prior run
        try:
            vm.check_and_record(
                Concept(
                    title="Titan Modular Skyscraper",
                    premise="High-rise construction using robotic tower cranes in Shinjuku",
                    building_type="Skyscraper",
                )
            )
            print("FAILED: ConceptTooSimilarError was not raised", file=sys.stderr)
            sys.exit(1)
        except ConceptTooSimilarError:
            pass

        # Verify novel concept succeeds
        vm.check_and_record(
            Concept(
                title="Deep Geo Borehole",
                premise="Subterranean geothermal excavation in Icelandic volcanic basalt",
                building_type="Infrastructure",
            )
        )
        if len(vm.history()) != 2:
            print(f"FAILED: Expected history len 2, got {len(vm.history())}", file=sys.stderr)
            sys.exit(1)

        print("STEP2_OK")
        sys.exit(0)


if __name__ == "__main__":
    asyncio.run(main())
