"""Planner port definition."""

from typing import Protocol

from smartmech.domain.capabilities import AdapterCapabilities
from smartmech.domain.concept import Plan


class PlannerPort(Protocol):
    """Protocol for generating the complete construction timelapse Plan."""

    @property
    def capabilities(self) -> AdapterCapabilities:
        """Declared adapter capabilities."""
        ...

    async def plan(self, prompt: str, seed: int) -> Plan:
        """Generate complete valid Plan adhering to all site and shot list invariants."""
        ...
