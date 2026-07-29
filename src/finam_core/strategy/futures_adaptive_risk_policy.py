from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class FuturesRiskProfile:
    asset: str
    symbol_prefixes: tuple[str, ...]
    min_stop_atr: float
    max_stop_atr: float
    target_atr: float
    min_reward_r: float
    structure_buffer_atr: float
    min_volume_ratio: float
    reference_stop_atr: float
    default_mode: str = "SHADOW"


@dataclass(frozen=True)
class FuturesRiskDecision:
    matched: bool
    asset: str | None
    mode: str
    allowed: bool
    reason: str
    stop_price: float | None = None
    take_price: float | None = None
    qty: float | None = None
    stop_atr: float | None = None
    take_atr: float | None = None
    reward_r: float | None = None
    volume_ratio: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class FuturesAdaptiveRiskPolicy:
    """Paper-only geometry and sizing policy for MOEX futures.

    The policy is pure: it never sends orders and does not know about REAL
    execution. Callers decide whether SHADOW recommendations are applied.
    """

    PROFILES = (
        FuturesRiskProfile("BR", ("BR",), 1.8, 2.5, 2.5, 1.5, 0.25, 1.30, 1.8, "ENFORCE"),
        FuturesRiskProfile("NG", ("NG",), 1.5, 2.2, 3.0, 1.7, 0.35, 1.50, 0.8, "SHADOW"),
        FuturesRiskProfile("USD", ("USDRUB", "USD"), 1.2, 1.8, 2.2, 1.5, 0.20, 1.15, 1.2, "SHADOW"),
        FuturesRiskProfile("CNY", ("CNYRUB", "CNY"), 1.2, 1.7, 2.0, 1.5, 0.20, 1.15, 1.2, "SHADOW"),
        FuturesRiskProfile("GOLD", ("GDU", "GD", "GLD", "GOLD"), 1.8, 2.5, 3.5, 1.8, 0.30, 1.25, 1.8, "SHADOW"),
    )

    def profile_for(self, symbol: str) -> FuturesRiskProfile | None:
        root = str(symbol or "").upper().split("@")[0]
        for profile in self.PROFILES:
            if any(root.startswith(prefix) for prefix in profile.symbol_prefixes):
                return profile
        return None

    def evaluate(
        self,
        *,
        symbol: str,
        side: str,
        entry_price: float,
        atr: float,
        qty: float,
        breakout_level: float | None = None,
        volume_ratio: float | None = None,
        roundtrip_cost_price: float | None = None,
        mode: str | None = None,
    ) -> FuturesRiskDecision:
        profile = self.profile_for(symbol)
        if profile is None:
            return FuturesRiskDecision(False, None, "OFF", True, "PROFILE_NOT_FOUND")

        effective_mode = str(mode or profile.default_mode).upper()
        side_u = str(side or "").upper()
        if side_u in {"LONG", "BUY"}:
            direction = 1.0
        elif side_u in {"SHORT", "SELL"}:
            direction = -1.0
        else:
            return FuturesRiskDecision(True, profile.asset, effective_mode, False, "SIDE_INVALID")

        price = float(entry_price or 0.0)
        atr_value = float(atr or 0.0)
        base_qty = abs(float(qty or 0.0))
        if price <= 0 or atr_value <= 0 or base_qty <= 0:
            return FuturesRiskDecision(True, profile.asset, effective_mode, False, "INPUT_INVALID")

        structure_distance = profile.min_stop_atr * atr_value
        if breakout_level is not None and float(breakout_level or 0.0) > 0:
            level = float(breakout_level)
            if direction > 0:
                structure_distance = price - (level - profile.structure_buffer_atr * atr_value)
            else:
                structure_distance = (level + profile.structure_buffer_atr * atr_value) - price

        stop_distance = min(
            max(structure_distance, profile.min_stop_atr * atr_value),
            profile.max_stop_atr * atr_value,
        )
        take_distance = max(profile.target_atr * atr_value, profile.min_reward_r * stop_distance)

        cost = max(0.0, float(roundtrip_cost_price or 0.0))
        if cost > 0 and take_distance < 3.0 * cost:
            return FuturesRiskDecision(
                True, profile.asset, effective_mode, False, "COST_BUFFER_BELOW_3X",
                stop_atr=stop_distance / atr_value,
                take_atr=take_distance / atr_value,
                reward_r=take_distance / stop_distance,
                volume_ratio=volume_ratio,
            )

        if volume_ratio is not None and float(volume_ratio) < profile.min_volume_ratio:
            return FuturesRiskDecision(
                True, profile.asset, effective_mode, False, "VOLUME_BELOW_PROFILE_THRESHOLD",
                stop_atr=stop_distance / atr_value,
                take_atr=take_distance / atr_value,
                reward_r=take_distance / stop_distance,
                volume_ratio=float(volume_ratio),
            )

        risk_qty = base_qty * profile.reference_stop_atr / (stop_distance / atr_value)
        adjusted_qty = min(base_qty, max(0.001, risk_qty))
        stop_price = price - direction * stop_distance
        take_price = price + direction * take_distance
        return FuturesRiskDecision(
            True,
            profile.asset,
            effective_mode,
            True,
            "PROFILE_PASS",
            stop_price=round(stop_price, 8),
            take_price=round(take_price, 8),
            qty=round(adjusted_qty, 6),
            stop_atr=round(stop_distance / atr_value, 6),
            take_atr=round(take_distance / atr_value, 6),
            reward_r=round(take_distance / stop_distance, 6),
            volume_ratio=None if volume_ratio is None else float(volume_ratio),
        )
