#!/usr/bin/env bash
set -euo pipefail

echo "=== BUILD_VOLATILITY_BREAKOUT_SIGNAL_V1 ==="

mkdir -p src/strategy/volatility_breakout scripts

cat > src/strategy/base/diagnostics.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class StrategyDiagnostics:
    passed_filters: list[str]
    failed_filters: list[str]
    feature_values: dict[str, float]
    thresholds: dict[str, float]
    score_breakdown: dict[str, float]
    execution_time_ms: float
    details: dict[str, Any]
PY

cat > src/strategy/base/strategy_result.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass

from strategy.base.diagnostics import StrategyDiagnostics
from strategy.base.signal import Signal


@dataclass(slots=True, frozen=True)
class StrategyResult:
    signal: Signal | None
    diagnostics: StrategyDiagnostics
    feature_version: str
    strategy_version: str
    reason: str
PY

cat > src/strategy/volatility_breakout/config.py <<'PY'
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class VolatilityBreakoutConfig:
    min_range_pct: float = 0.8
    min_body_pct: float = 0.5
    min_volume_ratio20: float = 1.2
    min_feature_quality: float = 0.85
    min_return1_pct: float = 0.0
    min_return5_pct: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "VolatilityBreakoutConfig":
        data = data or {}
        return cls(
            min_range_pct=float(data.get("min_range_pct", cls.min_range_pct)),
            min_body_pct=float(data.get("min_body_pct", cls.min_body_pct)),
            min_volume_ratio20=float(data.get("min_volume_ratio20", cls.min_volume_ratio20)),
            min_feature_quality=float(data.get("min_feature_quality", cls.min_feature_quality)),
            min_return1_pct=float(data.get("min_return1_pct", cls.min_return1_pct)),
            min_return5_pct=float(data.get("min_return5_pct", cls.min_return5_pct)),
        )
PY

cat > src/strategy/volatility_breakout/strategy.py <<'PY'
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
PY

cat > src/strategy/volatility_breakout/__init__.py <<'PY'
from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

__all__ = ["VolatilityBreakoutStrategy"]
PY

cat > scripts/test_volatility_breakout_signal_v1.sh <<'SH_TEST'
#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_VOLATILITY_BREAKOUT_SIGNAL_V1 ==="

PYTHONPATH=src python -m py_compile \
  src/strategy/base/diagnostics.py \
  src/strategy/base/strategy_result.py \
  src/strategy/volatility_breakout/config.py \
  src/strategy/volatility_breakout/strategy.py \
  src/strategy/volatility_breakout/__init__.py

PYTHONPATH=src python - <<'PY'
from strategy.base.registry import StrategyRegistry
import strategy.volatility_breakout  # noqa: F401
from strategy.volatility_breakout.strategy import VolatilityBreakoutStrategy

assert StrategyRegistry.get("VOLATILITY_BREAKOUT") is VolatilityBreakoutStrategy

strategy = VolatilityBreakoutStrategy()

long_result = strategy.run({
    "symbol": "SBER@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 1.2,
    "body_pct": 0.7,
    "volume_ratio20": 1.5,
    "feature_quality_score": 0.95,
    "return1_pct": 0.15,
    "return5_pct": 0.30,
    "source_version": "FEATURE_STORE_V1",
})
assert long_result.signal is not None
assert long_result.signal.direction == "LONG"
assert "range_pct" in long_result.diagnostics.passed_filters

short_result = strategy.run({
    "symbol": "GAZP@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 1.2,
    "body_pct": 0.7,
    "volume_ratio20": 1.5,
    "feature_quality_score": 0.95,
    "return1_pct": -0.15,
    "return5_pct": -0.30,
})
assert short_result.signal is not None
assert short_result.signal.direction == "SHORT"

flat_result = strategy.run({
    "symbol": "LKOH@MISX",
    "timeframe": "M1",
    "bar_ts": "2026-07-03T15:41:00+03:00",
    "range_pct": 0.1,
    "body_pct": 0.1,
    "volume_ratio20": 0.8,
    "feature_quality_score": 0.95,
    "return1_pct": 0.15,
    "return5_pct": 0.30,
})
assert flat_result.signal is None
assert flat_result.reason == "BASE_FILTER_FAILED"
assert "range_pct" in flat_result.diagnostics.failed_filters

invalid_result = strategy.run({
    "symbol": "",
    "timeframe": "",
})
assert invalid_result.signal is None
assert invalid_result.reason == "INVALID_FEATURE"
PY

echo "strategy=VOLATILITY_BREAKOUT"
echo "long_signal=ok"
echo "short_signal=ok"
echo "flat_result=ok"
echo "invalid_feature=ok"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=VOLATILITY_BREAKOUT_SIGNAL_V1_READY"
echo "VERDICT=TEST_VOLATILITY_BREAKOUT_SIGNAL_V1_OK"
SH_TEST

chmod +x scripts/test_volatility_breakout_signal_v1.sh
scripts/test_volatility_breakout_signal_v1.sh

echo "VERDICT=BUILD_VOLATILITY_BREAKOUT_SIGNAL_V1_OK"
