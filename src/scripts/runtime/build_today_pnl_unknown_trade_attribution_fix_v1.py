#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_FIX_V1
# Read-only диагностика сегодняшних trades с UNKNOWN strategy/timeframe.
# Скрипт строит план восстановления attribution, но не меняет БД.
# Для USDRUBF@RTSX ожидаемый fallback: strategy=USDRUB_REGIME, timeframe=LIVE.


UNKNOWN_TRADES_SQL = """
select
    id,
    created_at,
    ts,
    symbol,
    continuous_symbol,
    strategy,
    timeframe,
    side,
    qty,
    price,
    trade_source,
    origin,
    fill_id,
    payload
from trades
where created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
  )
order by created_at asc, id asc;
"""


NEIGHBOR_TRADES_SQL = """
select
    id,
    created_at,
    symbol,
    continuous_symbol,
    strategy,
    timeframe,
    side,
    qty,
    price,
    trade_source,
    origin,
    fill_id
from trades
where created_at::date = current_date
  and symbol = %s
  and id <> %s
  and strategy is not null
  and strategy not in ('UNKNOWN', 'UNKNOWN_STRATEGY')
  and timeframe is not null
  and timeframe not in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
order by abs(extract(epoch from (created_at - %s::timestamptz))) asc
limit 5;
"""


RUNTIME_UNIVERSE_SQL = """
select
    symbol,
    strategy,
    timeframe,
    is_enabled,
    source,
    updated_at
from runtime_active_universe
where symbol = %s
order by is_enabled desc, priority desc nulls last, updated_at desc nulls last
limit 1;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def parse_payload(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return value
    try:
        return json.loads(str(value))
    except Exception:
        return {}


def infer_from_payload(payload: dict[str, Any]) -> tuple[str, str, str]:
    # Русский комментарий:
    # Пробуем вытащить strategy/timeframe из разных известных мест payload.
    candidates = [
        payload,
        payload.get("trade_context_snapshot", {}) if isinstance(payload.get("trade_context_snapshot"), dict) else {},
        payload.get("risk_context", {}) if isinstance(payload.get("risk_context"), dict) else {},
        payload.get("signal", {}) if isinstance(payload.get("signal"), dict) else {},
        payload.get("raw", {}) if isinstance(payload.get("raw"), dict) else {},
    ]

    for item in candidates:
        strategy = norm(item.get("strategy") or item.get("strategy_name"))
        timeframe = norm(item.get("timeframe") or item.get("tf"))
        continuous_symbol = norm(item.get("continuous_symbol") or item.get("continuous"))

        if strategy or timeframe or continuous_symbol:
            return strategy, timeframe, continuous_symbol

    return "", "", ""


def fallback_for_symbol(symbol: str) -> tuple[str, str]:
    # Русский комментарий:
    # Жёсткий fallback только для известных активных production-paper маршрутов.
    mapping = {
        "USDRUBF@RTSX": ("USDRUB_REGIME", "LIVE"),
        "NGM6@RTSX": ("NG_CONSERVATIVE_BREAKOUT_M1", "LIVE"),
        "NGN6@RTSX": ("NG_CONSERVATIVE_BREAKOUT_M1", "LIVE"),
        "BRN6@RTSX": ("BR_CONSERVATIVE_BREAKOUT", "LIVE"),
    }
    return mapping.get(symbol, ("", ""))


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    print("=== TODAY PNL UNKNOWN TRADE ATTRIBUTION FIX V1 ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(UNKNOWN_TRADES_SQL)
            unknown_rows = cur.fetchall()

            plan_rows: list[dict[str, Any]] = []

            for row in unknown_rows:
                symbol = norm(row.get("symbol"))
                payload = parse_payload(row.get("payload"))

                payload_strategy, payload_timeframe, payload_continuous = infer_from_payload(payload)

                cur.execute(RUNTIME_UNIVERSE_SQL, (symbol,))
                runtime_row = cur.fetchone()

                cur.execute(NEIGHBOR_TRADES_SQL, (symbol, row.get("id"), row.get("created_at")))
                neighbors = cur.fetchall()

                runtime_strategy = norm(runtime_row.get("strategy")) if runtime_row else ""
                runtime_timeframe = norm(runtime_row.get("timeframe")) if runtime_row else ""

                fallback_strategy, fallback_timeframe = fallback_for_symbol(symbol)

                neighbor_strategy = ""
                neighbor_timeframe = ""
                if neighbors:
                    neighbor_strategy = norm(neighbors[0].get("strategy"))
                    neighbor_timeframe = norm(neighbors[0].get("timeframe"))

                planned_strategy = (
                    payload_strategy
                    or runtime_strategy
                    or neighbor_strategy
                    or fallback_strategy
                    or "UNKNOWN"
                )
                planned_timeframe = (
                    payload_timeframe
                    or runtime_timeframe
                    or neighbor_timeframe
                    or fallback_timeframe
                    or "UNKNOWN"
                )
                planned_continuous = (
                    payload_continuous
                    or norm(row.get("continuous_symbol"))
                    or symbol
                )

                confidence = "LOW"
                source = "none"

                if payload_strategy and payload_timeframe:
                    confidence = "HIGH"
                    source = "payload"
                elif runtime_strategy and runtime_timeframe:
                    confidence = "HIGH"
                    source = "runtime_active_universe"
                elif neighbor_strategy and neighbor_timeframe:
                    confidence = "MEDIUM"
                    source = "neighbor_trade"
                elif fallback_strategy and fallback_timeframe:
                    confidence = "MEDIUM"
                    source = "known_symbol_fallback"

                plan_rows.append(
                    {
                        "id": row.get("id"),
                        "created_at": row.get("created_at"),
                        "symbol": symbol,
                        "side": row.get("side"),
                        "qty": row.get("qty"),
                        "price": row.get("price"),
                        "old_strategy": norm(row.get("strategy")) or "NULL",
                        "old_timeframe": norm(row.get("timeframe")) or "NULL",
                        "old_continuous_symbol": norm(row.get("continuous_symbol")) or "NULL",
                        "planned_strategy": planned_strategy,
                        "planned_timeframe": planned_timeframe,
                        "planned_continuous_symbol": planned_continuous,
                        "source": source,
                        "confidence": confidence,
                        "neighbor_count": len(neighbors),
                        "runtime_match": 1 if runtime_row else 0,
                    }
                )

    print("TODAY_PNL_UNKNOWN_ATTRIBUTION_ROWS")
    for p in plan_rows:
        print(
            "TODAY_PNL_UNKNOWN_ATTRIBUTION_ROW "
            f"id={p['id']} "
            f"created_at={p['created_at']} "
            f"symbol={p['symbol']} "
            f"side={p['side']} "
            f"qty={p['qty']} "
            f"price={p['price']} "
            f"old_strategy={p['old_strategy']} "
            f"old_timeframe={p['old_timeframe']} "
            f"planned_strategy={p['planned_strategy']} "
            f"planned_timeframe={p['planned_timeframe']} "
            f"planned_continuous_symbol={p['planned_continuous_symbol']} "
            f"source={p['source']} "
            f"confidence={p['confidence']} "
            f"runtime_match={p['runtime_match']} "
            f"neighbor_count={p['neighbor_count']}"
        )

    apply_candidates = [
        p for p in plan_rows
        if p["planned_strategy"] != "UNKNOWN"
        and p["planned_timeframe"] != "UNKNOWN"
        and p["confidence"] in ("HIGH", "MEDIUM")
    ]

    high_conf = sum(1 for p in apply_candidates if p["confidence"] == "HIGH")
    medium_conf = sum(1 for p in apply_candidates if p["confidence"] == "MEDIUM")

    print()
    print("TODAY_PNL_UNKNOWN_ATTRIBUTION_SUMMARY")
    print(f"unknown_rows={len(plan_rows)}")
    print(f"apply_candidates={len(apply_candidates)}")
    print(f"high_confidence={high_conf}")
    print(f"medium_confidence={medium_conf}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")

    if len(plan_rows) == 0:
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_CLEAN")
    elif len(apply_candidates) == len(plan_rows):
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_PLAN_READY")
    else:
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_REVIEW_REQUIRED")

    print("TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_FIX_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
