# src/finam_core/risk/unified_decision.py

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass
class UnifiedRiskDecision:
    """
    Русский коммент: единый формат решения risk-stack.
    Используется для kill switch, portfolio heat, RiskEngine и будущих risk-слоёв.
    """

    allowed: bool
    layer: str
    reason: str
    symbol: str | None = None
    side: str | None = None
    qty: float | None = None
    payload: dict[str, Any] = field(default_factory=dict)
    ts: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @classmethod
    def allow(cls, layer: str, reason: str = "ok", **kwargs) -> "UnifiedRiskDecision":
        return cls(allowed=True, layer=layer, reason=reason, **kwargs)

    @classmethod
    def reject(cls, layer: str, reason: str, **kwargs) -> "UnifiedRiskDecision":
        return cls(allowed=False, layer=layer, reason=reason, **kwargs)

    def to_dict(self) -> dict[str, Any]:
        return {
            "allowed": self.allowed,
            "layer": self.layer,
            "reason": self.reason,
            "symbol": self.symbol,
            "side": self.side,
            "qty": self.qty,
            "payload": self.payload,
            "ts": self.ts,
        }


class RiskDecisionRecorder:
    """
    Русский коммент: единая точка stdout + PostgreSQL logging для risk decisions.
    """

    def __init__(self, pg_logger=None):
        self.pg_logger = pg_logger

    def emit(self, decision: UnifiedRiskDecision) -> None:
        status = "OK" if decision.allowed else "REJECT"

        print(
            f"PIPE_RISK_DECISION status={status} "
            f"layer={decision.layer} "
            f"reason={decision.reason} "
            f"symbol={decision.symbol} "
            f"side={decision.side} "
            f"qty={decision.qty}",
            flush=True,
        )

        if self.pg_logger is not None:
            self.pg_logger.log_risk_event(
                symbol=decision.symbol,
                event=f"{decision.layer}_{status.lower()}",
                decision=decision.reason,
                payload=decision.to_dict(),
            )
