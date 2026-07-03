from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskModuleResult:
    module: str
    status: str
    score: int
    reason: str
    details: dict[str, str]


class RiskModule:
    name = "BASE"

    def evaluate(self, ctx) -> RiskModuleResult:
        raise NotImplementedError
