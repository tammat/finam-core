from dataclasses import dataclass
from datetime import datetime
from typing import Any

from finam_core.analytics.validated_profile import is_validated_profile


@dataclass(frozen=True)
class EdgeGateDecision:
    allowed: bool
    reason: str
    symbol: str
    strategy: str
    timeframe: str
    hour_utc: int


def _read_attr(obj: Any, name: str, default: str = "") -> str:
    # Безопасно читаем поле как из dataclass/object, так и из dict.
    if isinstance(obj, dict):
        return str(obj.get(name) or default)
    return str(getattr(obj, name, default) or default)


def evaluate_edge_execution_gate(signal: Any, ts: datetime) -> EdgeGateDecision:
    # Детерминированный статистический gate:
    # пропускает только заранее валидированные профили edge.
    symbol = _read_attr(signal, "symbol")
    strategy = _read_attr(signal, "strategy")
    timeframe = _read_attr(signal, "timeframe")

    hour_utc = int(ts.hour)

    if not symbol:
        return EdgeGateDecision(False, "missing_symbol", symbol, strategy, timeframe, hour_utc)

    if not strategy:
        return EdgeGateDecision(False, "missing_strategy", symbol, strategy, timeframe, hour_utc)

    if not timeframe:
        return EdgeGateDecision(False, "missing_timeframe", symbol, strategy, timeframe, hour_utc)

    if is_validated_profile(
        symbol=symbol,
        strategy=strategy,
        timeframe=timeframe,
        hour_utc=hour_utc,
    ):
        return EdgeGateDecision(True, "validated_profile", symbol, strategy, timeframe, hour_utc)

    return EdgeGateDecision(False, "unvalidated_profile", symbol, strategy, timeframe, hour_utc)
