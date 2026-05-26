from dataclasses import asdict
from datetime import datetime
from typing import Any, Dict

from finam_core.execution.edge_execution_gate import EdgeGateDecision


def build_edge_telemetry_snapshot(
    decision: EdgeGateDecision,
    ts: datetime,
    mode: str,
) -> Dict[str, Any]:
    # Формируем детерминированный telemetry snapshot для payload/trade_context_snapshot.
    # Модуль ничего не пишет в БД и не влияет на execution.
    return {
        "edge_gate": {
            "mode": mode,
            "allowed": decision.allowed,
            "reason": decision.reason,
            "symbol": decision.symbol,
            "strategy": decision.strategy,
            "timeframe": decision.timeframe,
            "hour_utc": decision.hour_utc,
            "ts_utc": ts.isoformat(),
            "decision": asdict(decision),
        }
    }


def merge_edge_telemetry(
    payload: Dict[str, Any],
    telemetry: Dict[str, Any],
) -> Dict[str, Any]:
    # Безопасно добавляем edge telemetry в существующий payload.
    result = dict(payload or {})

    context = dict(result.get("trade_context_snapshot") or {})
    context.update(telemetry)

    result["trade_context_snapshot"] = context

    return result
