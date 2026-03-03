from dataclasses import dataclass, field
from typing import Set


@dataclass(frozen=True)
class RiskConfig:
    """
    Deterministic risk configuration.

    All values expressed in absolute units or fractions.
    """

    # --- Capital control ---
    max_risk_per_trade: float  # fraction of equity (e.g. 0.01 = 1%)
    max_total_exposure: float  # absolute exposure limit (in currency units)
    daily_loss_limit: float    # absolute daily loss limit (in currency units)

    # --- Position control ---
    max_position_per_symbol: float  # max notional per symbol
    allowed_symbols: Set[str] = field(default_factory=set)

    # --- Safety switches ---
    trading_enabled: bool = True

    def __post_init__(self):
        if not (0 < self.max_risk_per_trade <= 1):
            raise ValueError("max_risk_per_trade must be in (0, 1]")

        if self.max_total_exposure <= 0:
            raise ValueError("max_total_exposure must be positive")

        if self.daily_loss_limit <= 0:
            raise ValueError("daily_loss_limit must be positive")

        if self.max_position_per_symbol <= 0:
            raise ValueError("max_position_per_symbol must be positive")

        if not isinstance(self.allowed_symbols, set):
            raise TypeError("allowed_symbols must be a set")

    def is_symbol_allowed(self, symbol: str) -> bool:
        if not self.allowed_symbols:
            return True
        return symbol in self.allowed_symbols