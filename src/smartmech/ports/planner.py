"""Planner port definition."""

from typing import Protocol

from smartmech.domain.adapter_identity import AdapterIdentity
from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import Plan


class PlannerPort(Protocol):
    """Protocol for generating the complete construction timelapse Plan."""

    @property
    def identity(self) -> AdapterIdentity:
        """Declared adapter identity."""
        ...

    @property
    def cost_estimate_per_call(self) -> float:
        """Estimated cost units per invocation."""
        ...

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Declared adapter capabilities."""
        ...

    async def plan(self, prompt: str, seed: int) -> Plan:
        """Generate complete valid Plan adhering to all site and shot list invariants."""
        ...
