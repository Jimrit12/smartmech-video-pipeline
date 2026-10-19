"""Budget guard policy enforcing per-run and per-day cost ceilings."""

from smartmech.domain.budget import BudgetConfig, BudgetExceededError, CostRecord
from smartmech.ports.cost_ledger import CostLedgerPort


class BudgetGuard:
    """Enforces cost controls and hard limits before and after adapter operations."""

    def __init__(self, ledger: CostLedgerPort, config: BudgetConfig) -> None:
        self.ledger = ledger
        self.config = config

    async def check_budget_before_call(self, run_id: str, estimated_cost: float) -> None:
        """Pre-execution budget check: raises BudgetExceededError if limit would be breached."""
        run_spend = await self.ledger.get_run_cost(run_id)
        if run_spend + estimated_cost > self.config.per_run_budget:
            raise BudgetExceededError(
                f"Operation would exceed per-run budget: {run_spend + estimated_cost:.2f} > {self.config.per_run_budget:.2f}",
                run_id=run_id,
                current_spend=run_spend,
                limit=self.config.per_run_budget,
            )

        daily_spend = await self.ledger.get_daily_cost()
        if daily_spend + estimated_cost > self.config.per_day_budget:
            raise BudgetExceededError(
                f"Operation would exceed per-day budget: {daily_spend + estimated_cost:.2f} > {self.config.per_day_budget:.2f}",
                run_id=run_id,
                current_spend=daily_spend,
                limit=self.config.per_day_budget,
            )

    async def record_spend(self, record: CostRecord) -> None:
        """Record spend into the ledger and verify limits."""
        await self.ledger.record_cost(record)
