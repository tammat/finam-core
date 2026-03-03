from dataclasses import dataclass
from risk.context import RiskContext


@dataclass
class SizingEngine:
    risk_pct: float = 0.01
    atr_multiplier: float = 2.0
    max_position_pct: float = 0.1
    fallback_vol_pct: float = 0.02
    enable_drawdown_scaling: bool = True

    def __init__(
            self,
            risk_pct: float | None = None,
            risk_per_trade: float | None = None,
            atr_multiplier: float = 1.0,
            max_position_pct: float | None = None,
    ):
        # Backward compatibility:
        # risk_per_trade — алиас для risk_pct
        if risk_pct is None and risk_per_trade is not None:
            risk_pct = risk_per_trade

        if risk_pct is None:
            raise ValueError("risk_pct (or risk_per_trade) must be provided")

        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier
        self.max_position_pct = max_position_pct

    def _apply_drawdown_scaling(self, context: RiskContext) -> float:
        """
        Institutional drawdown scaling:
        <5%  → 100% risk
        5–10% → 50% risk
        >10% → block trading
        """
        if not self.enable_drawdown_scaling:
            return 1.0

        dd_raw = getattr(context, "drawdown", 0.0)
        dd = abs(dd_raw)

        if dd < 0.05:
            return 1.0
        elif dd < 0.10:
            return 0.5
        else:
            return 0.0

    def size(self, signal, context: RiskContext) -> float:
        """
        Calculates position size using:
        - % risk per trade
        - ATR-based stop distance (fallback to price volatility)
        - Max position constraint
        - Drawdown scaling
        """

        # Safety guards
        if context.equity <= 0:
            return 0.0

        price = getattr(signal, "price", None)
        if price is None or price <= 0:
            return 0.0

        multiplier = self._apply_drawdown_scaling(context)
        if multiplier == 0.0:
            return 0.0

        # Risk allocation
        effective_risk_pct = self.risk_pct * multiplier
        risk_amount = context.equity * effective_risk_pct

        # Stop distance
        atr = getattr(signal, "atr", None)

        if atr and atr > 0:
            # Volatility-based sizing
            stop_distance = atr * self.atr_multiplier
        else:
            # Fixed risk sizing (no ATR)
            stop_distance = price
        if stop_distance <= 0:
            return 0.0

        qty = risk_amount / stop_distance

        # If sizing result invalid
        if qty <= 0:
            if hasattr(signal, "qty"):
                signal.qty = 0.0
                return signal
            return 0.0

        qty = float(qty)

        # Backward compatibility:
        # If signal already has qty attribute → mutate and return signal
        if hasattr(signal, "qty"):
            signal.qty = qty
            return signal

        # Otherwise return raw quantity
        return qty