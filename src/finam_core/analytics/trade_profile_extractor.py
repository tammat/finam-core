from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional
import json


@dataclass(frozen=True)
class TradeProfileRow:
    trade_id: Optional[int]
    symbol: str
    side: str
    qty: float
    price: float
    realized_pnl: float
    strategy: str
    regime: str
    session: str
    entry_reason: str
    exit_reason: str
    raw_context: Dict[str, Any]


def _as_dict(value: Any) -> Dict[str, Any]:
    # Приводим raw_json из PostgreSQL к dict независимо от того,
    # пришел ли он уже как jsonb/dict или строкой.
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            return {}
    return {}


def _get_nested(data: Dict[str, Any], *path: str, default: Any = "") -> Any:
    # Безопасное чтение вложенных полей trade_context_snapshot.
    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return default
        current = current.get(key)
    return default if current is None else current


def extract_trade_profile_rows(rows: Iterable[Dict[str, Any]]) -> List[TradeProfileRow]:
    result: List[TradeProfileRow] = []

    for row in rows:
        raw_json = _as_dict(row.get("raw_json"))
        context = _as_dict(raw_json.get("trade_context_snapshot"))

        strategy = (
            _get_nested(context, "strategy", default="")
            or raw_json.get("strategy")
            or row.get("strategy")
            or ""
        )

        regime = (
            _get_nested(context, "regime", default="")
            or _get_nested(context, "regime_state", "regime", default="")
            or raw_json.get("regime")
            or ""
        )

        session = (
            _get_nested(context, "session", default="")
            or raw_json.get("session")
            or ""
        )

        entry_reason = (
            _get_nested(context, "entry_reason", default="")
            or raw_json.get("entry_reason")
            or raw_json.get("reason")
            or ""
        )

        exit_reason = (
            _get_nested(context, "exit_reason", default="")
            or raw_json.get("exit_reason")
            or ""
        )

        result.append(
            TradeProfileRow(
                trade_id=row.get("id"),
                symbol=str(row.get("symbol") or ""),
                side=str(row.get("side") or ""),
                qty=float(row.get("qty") or row.get("quantity") or 0.0),
                price=float(row.get("price") or 0.0),
                realized_pnl=float(row.get("realized_pnl") or row.get("pnl") or 0.0),
                strategy=str(strategy),
                regime=str(regime),
                session=str(session),
                entry_reason=str(entry_reason),
                exit_reason=str(exit_reason),
                raw_context=context,
            )
        )

    return result
