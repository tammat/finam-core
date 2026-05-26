from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DirectionalEdgeDecision:
    mode: str
    status: str
    reason: str
    symbol: str
    continuous_symbol: str
    strategy: str
    timeframe: str
    side: str
    regime_direction: str
    guard_status: str | None = None


class DirectionalEdgeGuard:
    """Русский комментарий: analytics-only/soft advisory guard без блокировки execution."""

    def __init__(self, mode: str = "soft_advisory"):
        self.mode = mode

    def decide(
        self,
        *,
        symbol: str,
        continuous_symbol: str,
        strategy: str,
        timeframe: str,
        side: str,
        regime_direction: str,
        guard_status: str | None,
    ) -> DirectionalEdgeDecision:
        normalized_side = str(side or "").upper()
        normalized_regime = str(regime_direction or "unknown").lower()
        normalized_guard = str(guard_status or "unknown").lower()

        if normalized_guard == "unknown":
            return DirectionalEdgeDecision(
                mode=self.mode,
                status="unknown",
                reason="directional_edge_guard_missing",
                symbol=symbol,
                continuous_symbol=continuous_symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=normalized_side,
                regime_direction=normalized_regime,
                guard_status=guard_status,
            )

        if normalized_guard == "insufficient_data":
            return DirectionalEdgeDecision(
                mode=self.mode,
                status="insufficient_data",
                reason="directional_edge_sample_below_threshold",
                symbol=symbol,
                continuous_symbol=continuous_symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=normalized_side,
                regime_direction=normalized_regime,
                guard_status=guard_status,
            )

        expected_side = self._expected_side_for_regime(normalized_regime)

        if expected_side is None:
            return DirectionalEdgeDecision(
                mode=self.mode,
                status="unknown",
                reason="directional_edge_regime_not_mapped",
                symbol=symbol,
                continuous_symbol=continuous_symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=normalized_side,
                regime_direction=normalized_regime,
                guard_status=guard_status,
            )

        if normalized_guard == "favorable" and normalized_side == expected_side:
            return DirectionalEdgeDecision(
                mode=self.mode,
                status="confirmed",
                reason="EDGE_DIRECTION_CONFIRMED",
                symbol=symbol,
                continuous_symbol=continuous_symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=normalized_side,
                regime_direction=normalized_regime,
                guard_status=guard_status,
            )

        if normalized_guard == "unfavorable":
            return DirectionalEdgeDecision(
                mode=self.mode,
                status="mismatch",
                reason="EDGE_DIRECTION_MISMATCH",
                symbol=symbol,
                continuous_symbol=continuous_symbol,
                strategy=strategy,
                timeframe=timeframe,
                side=normalized_side,
                regime_direction=normalized_regime,
                guard_status=guard_status,
            )

        return DirectionalEdgeDecision(
            mode=self.mode,
            status="neutral",
            reason="directional_edge_neutral",
            symbol=symbol,
            continuous_symbol=continuous_symbol,
            strategy=strategy,
            timeframe=timeframe,
            side=normalized_side,
            regime_direction=normalized_regime,
            guard_status=guard_status,
        )

    @staticmethod
    def _expected_side_for_regime(regime_direction: str) -> str | None:
        if regime_direction == "trend_down":
            return "SELL"
        if regime_direction == "trend_up":
            return "BUY"
        return None
