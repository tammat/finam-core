from dataclasses import dataclass

@dataclass(frozen=True)
class RiskConfig:
    max_position_qty: float | None = None
    max_notional: float | None = None
    max_daily_loss: float | None = None