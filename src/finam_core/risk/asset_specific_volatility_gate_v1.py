from __future__ import annotations

from dataclasses import dataclass


ASSET_BY_SYMBOL = {
    "USDRUBF@RTSX": "USD",
    "CNYRUBF@RTSX": "CNY",
    "GDU6@RTSX": "GOLD",
}


@dataclass(frozen=True)
class AssetVolatilityDecisionV1:
    applies: bool
    allowed: bool
    asset_code: str
    reason_code: str
    atr_pct: float
    atr_percentile: float
    minimum_percentile: float
    maximum_percentile: float
    mode: str = "OWN_HISTORY_ATR_PERCENTILE_V1"


class AssetSpecificVolatilityGateV1:
    """Normalize volatility against each instrument's own closed-bar history."""

    BOUNDS = {
        "USD": (0.10, 0.98),
        "CNY": (0.10, 0.98),
        "GOLD": (0.15, 0.98),
    }

    def decide(
        self,
        *,
        symbol: str,
        atr_pct: float,
        atr_percentile: float,
        data_ready: bool,
        stale: bool,
    ) -> AssetVolatilityDecisionV1:
        asset = ASSET_BY_SYMBOL.get(str(symbol or "").upper(), "")
        if not asset:
            return AssetVolatilityDecisionV1(
                False, False, "", "ASSET_GATE_NOT_APPLICABLE", float(atr_pct or 0),
                float(atr_percentile or 0), 0, 1,
            )
        minimum, maximum = self.BOUNDS[asset]
        percentile = float(atr_percentile or 0)
        atr_value = float(atr_pct or 0)
        if not data_ready or stale or atr_value <= 0:
            allowed, reason = False, f"{asset}_VOLATILITY_HISTORY_NOT_READY"
        elif percentile < minimum:
            allowed, reason = False, f"{asset}_VOLATILITY_BELOW_OWN_HISTORY"
        elif percentile > maximum:
            allowed, reason = False, f"{asset}_VOLATILITY_EXTREME_TAIL"
        else:
            allowed, reason = True, f"{asset}_VOLATILITY_OWN_HISTORY_OK"
        return AssetVolatilityDecisionV1(
            True, allowed, asset, reason, atr_value, percentile, minimum, maximum
        )
