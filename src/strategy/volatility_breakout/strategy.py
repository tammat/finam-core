from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from strategy.base.diagnostics import StrategyDiagnostics
from strategy.base.registry import StrategyRegistry
from strategy.base.signal import Signal
from strategy.base.strategy import Strategy
from strategy.base.strategy_result import StrategyResult
from strategy.volatility_breakout.config import VolatilityBreakoutConfig


def _num(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _ts(value: object) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str) and value:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return datetime.now(timezone.utc)
    return datetime.now(timezone.utc)


def _score_ratio(value: float, threshold: float) -> float:
    if threshold <= 0:
        return 1.0
    return max(0.0, min(1.0, value / threshold / 2.0))


@StrategyRegistry.register
class VolatilityBreakoutStrategy(Strategy):
    name = "Volatility Breakout"
    family = "VOLATILITY_BREAKOUT"
    version = "v1"
    enabled = True

    def __init__(self, config: VolatilityBreakoutConfig | None = None) -> None:
        self.config = config or VolatilityBreakoutConfig()

    def run(self, feature_snapshot: dict[str, Any]) -> StrategyResult:
        started = time.perf_counter()
        cfg = self.config

        symbol = str(feature_snapshot.get("symbol") or "")
        timeframe = str(feature_snapshot.get("timeframe") or "")

        if not symbol or not timeframe:
            diagnostics = StrategyDiagnostics(
                passed_filters=[],
                failed_filters=["symbol", "timeframe"],
                feature_values={},
                thresholds={},
                score_breakdown={},
                execution_time_ms=(time.perf_counter() - started) * 1000.0,
                details={"error": "symbol_or_timeframe_missing"},
            )
            return StrategyResult(
                signal=None,
                diagnostics=diagnostics,
                feature_version=str(feature_snapshot.get("source_version") or "FEATURE_STORE_V1"),
                strategy_version=self.version,
                reason="INVALID_FEATURE",
            )

        signal_ts = _ts(feature_snapshot.get("bar_ts"))

        values = {
            "range_pct": _num(feature_snapshot.get("range_pct")),
            "body_pct": _num(feature_snapshot.get("body_pct")),
            "volume_ratio20": _num(feature_snapshot.get("volume_ratio20")),
            "feature_quality_score": _num(feature_snapshot.get("feature_quality_score")),
            "return1_pct": _num(feature_snapshot.get("return1_pct")),
            "return5_pct": _num(feature_snapshot.get("return5_pct")),
        }

        thresholds = {
            "min_range_pct": cfg.min_range_pct,
            "min_body_pct": cfg.min_body_pct,
            "min_volume_ratio20": cfg.min_volume_ratio20,
            "min_feature_quality": cfg.min_feature_quality,
            "min_return1_pct": cfg.min_return1_pct,
            "min_return5_pct": cfg.min_return5_pct,
        }

        checks = {
            "range_pct": values["range_pct"] >= cfg.min_range_pct,
            "body_pct": values["body_pct"] >= cfg.min_body_pct,
            "volume_ratio20": values["volume_ratio20"] >= cfg.min_volume_ratio20,
            "feature_quality_score": values["feature_quality_score"] >= cfg.min_feature_quality,
        }

        passed = [k for k, ok in checks.items() if ok]
        failed = [k for k, ok in checks.items() if not ok]
        base_ok = not failed

        long_ok = (
            values["return1_pct"] > cfg.min_return1_pct
            and values["return5_pct"] > cfg.min_return5_pct
        )
        short_ok = (
            values["return1_pct"] < -cfg.min_return1_pct
            and values["return5_pct"] < -cfg.min_return5_pct
        )

        if long_ok:
            passed.append("long_return")
        elif short_ok:
            passed.append("short_return")
        else:
            failed.append("direction_return")

        range_score = _score_ratio(values["range_pct"], cfg.min_range_pct)
        body_score = _score_ratio(values["body_pct"], cfg.min_body_pct)
        volume_score = _score_ratio(values["volume_ratio20"], cfg.min_volume_ratio20)
        quality_score = max(0.0, min(1.0, values["feature_quality_score"]))

        total_score = max(
            0.0,
            min(1.0, (range_score + body_score + volume_score + quality_score) / 4.0),
        )

        score_breakdown = {
            "range_score": range_score,
            "body_score": body_score,
            "volume_score": volume_score,
            "quality_score": quality_score,
            "total_score": total_score,
        }

        direction = "FLAT"
        reason = "NO_SIGNAL"
        signal: Signal | None = None

        if base_ok and long_ok:
            direction = "LONG"
            reason = "LONG_VOLATILITY_BREAKOUT"
        elif base_ok and short_ok:
            direction = "SHORT"
            reason = "SHORT_VOLATILITY_BREAKOUT"
        elif not base_ok:
            reason = "BASE_FILTER_FAILED"

        if direction in {"LONG", "SHORT"}:
            signal = Signal(
                symbol=symbol,
                timeframe=timeframe,
                strategy_family=self.family,
                signal_ts=signal_ts,
                direction=direction,
                strength=total_score,
                score=total_score,
                confidence=total_score,
            )

        elapsed_ms = (time.perf_counter() - started) * 1000.0

        diagnostics = StrategyDiagnostics(
            passed_filters=passed,
            failed_filters=failed,
            feature_values=values,
            thresholds=thresholds,
            score_breakdown=score_breakdown,
            execution_time_ms=elapsed_ms,
            details={"direction": direction},
        )

        return StrategyResult(
            signal=signal,
            diagnostics=diagnostics,
            feature_version=str(feature_snapshot.get("source_version") or "FEATURE_STORE_V1"),
            strategy_version=self.version,
            reason=reason,
        )
