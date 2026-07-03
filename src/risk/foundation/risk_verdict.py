from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RiskVerdict:
    status: str
    risk_score: int
    reasons: tuple[str, ...]

    def is_pass(self) -> bool:
        return self.status == "PASS"
