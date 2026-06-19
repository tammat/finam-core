#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_V1

Read-only scorecard по накопленной истории пробойных сигналов.
Ничего не пишет в БД, не включает runtime/execution, не отправляет Telegram.
"""

import json
import os
import sys
from decimal import Decimal
from typing import Any, Dict, List

import psycopg2
import psycopg2.extras


def _f(v: Any) -> float:
    if v is None:
        return 0.0
    if isinstance(v, Decimal):
        return float(v)
    return float(v)


def _edge_status(signals_total: int, ready_total: int, avg_follow_5m: float | None) -> str:
    if ready_total < 20:
        return "INSUFFICIENT_DATA"
    if avg_follow_5m is None:
        return "NO_FOLLOW_THROUGH_DATA"
    if avg_follow_5m > 0:
        return "EDGE_POSITIVE"
    if avg_follow_5m < 0:
        return "EDGE_NEGATIVE"
    return "EDGE_NEUTRAL"


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            # Базовая статистика по накопленной истории наблюдений.
            cur.execute(
                """
                with rows as (
                    select
                        coalesce(symbol, 'UNKNOWN') as symbol,
                        coalesce(asset_class, 'UNKNOWN') as asset_class,
                        coalesce(timeframe, 'UNKNOWN') as timeframe,
                        'BREAKOUT_READY' as signal_class,
                        coalesce(status, '') as status,
                        (coalesce(status, '') = 'BREAKOUT_READY') as is_breakout_ready,
                        created_at
                    from analytics_multi_asset_breakout_row_v1
                    where created_at >= now() - interval '7 days'
                )
                select
                    symbol,
                    asset_class,
                    timeframe,
                    signal_class,
                    count(*) as observations_total,
                    sum(case when is_breakout_ready then 1 else 0 end) as ready_total,
                    round(
                        100.0 * sum(case when is_breakout_ready then 1 else 0 end)::numeric
                        / nullif(count(*), 0),
                        4
                    ) as ready_rate_pct,
                    max(created_at) as last_seen
                from rows
                group by symbol, asset_class, timeframe, signal_class
                order by ready_total desc, observations_total desc, symbol
                """
            )
            rows: List[Dict[str, Any]] = [dict(r) for r in cur.fetchall()]

            # Follow-through, если таблица уже есть и содержит данные.
            cur.execute(
                """
                select to_regclass('public.analytics_multi_asset_breakout_follow_through_v1') is not null as exists
                """
            )
            ft_exists = bool(cur.fetchone()["exists"])

            ft_by_symbol: Dict[str, Dict[str, Any]] = {}

            if ft_exists:
                cur.execute(
                    """
                    select
                        coalesce(symbol, 'UNKNOWN') as symbol,
                        count(*) as follow_rows,
                        avg(return_pct) filter (where horizon_min = 3) as ret_3m_avg,
                        avg(return_pct) filter (where horizon_min = 5) as ret_5m_avg,
                        avg(return_pct) filter (where horizon_min = 10) as ret_10m_avg,
                        avg(return_pct) filter (where horizon_min = 15) as ret_15m_avg,
                        avg(case when direction_ok then 1.0 else 0.0 end) filter (where horizon_min = 3) as winrate_3m,
                        avg(case when direction_ok then 1.0 else 0.0 end) filter (where horizon_min = 5) as winrate_5m,
                        avg(case when direction_ok then 1.0 else 0.0 end) filter (where horizon_min = 10) as winrate_10m,
                        avg(case when direction_ok then 1.0 else 0.0 end) filter (where horizon_min = 15) as winrate_15m
                    from analytics_multi_asset_breakout_follow_through_v1
                    where created_at >= now() - interval '7 days'
                    group by symbol
                    """
                )
                for r in cur.fetchall():
                    ft_by_symbol[str(r["symbol"])] = dict(r)

    scorecard: List[Dict[str, Any]] = []

    for r in rows:
        symbol = str(r["symbol"])
        ft = ft_by_symbol.get(symbol, {})
        ready_total = int(r["ready_total"] or 0)
        observations_total = int(r["observations_total"] or 0)
        ret_5m_avg = ft.get("ret_5m_avg")

        item = {
            "symbol": symbol,
            "asset_class": r["asset_class"],
            "timeframe": r["timeframe"],
            "signal_class": r["signal_class"],
            "observations_total": observations_total,
            "ready_total": ready_total,
            "ready_rate_pct": _f(r["ready_rate_pct"]),
            "follow_rows": int(ft.get("follow_rows") or 0),
            "ret_3m_avg": None if ft.get("ret_3m_avg") is None else _f(ft.get("ret_3m_avg")),
            "ret_5m_avg": None if ret_5m_avg is None else _f(ret_5m_avg),
            "ret_10m_avg": None if ft.get("ret_10m_avg") is None else _f(ft.get("ret_10m_avg")),
            "ret_15m_avg": None if ft.get("ret_15m_avg") is None else _f(ft.get("ret_15m_avg")),
            "winrate_3m": None if ft.get("winrate_3m") is None else _f(ft.get("winrate_3m")),
            "winrate_5m": None if ft.get("winrate_5m") is None else _f(ft.get("winrate_5m")),
            "winrate_10m": None if ft.get("winrate_10m") is None else _f(ft.get("winrate_10m")),
            "winrate_15m": None if ft.get("winrate_15m") is None else _f(ft.get("winrate_15m")),
            "edge_status": _edge_status(observations_total, ready_total, None if ret_5m_avg is None else _f(ret_5m_avg)),
        }
        scorecard.append(item)

    ready_total_all = sum(int(x["ready_total"]) for x in scorecard)
    observations_total_all = sum(int(x["observations_total"]) for x in scorecard)

    result = {
        "verdict": "MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "rows_total": len(scorecard),
        "observations_total": observations_total_all,
        "ready_total": ready_total_all,
        "edge_positive": sum(1 for x in scorecard if x["edge_status"] == "EDGE_POSITIVE"),
        "edge_negative": sum(1 for x in scorecard if x["edge_status"] == "EDGE_NEGATIVE"),
        "insufficient_data": sum(1 for x in scorecard if x["edge_status"] == "INSUFFICIENT_DATA"),
        "scorecard": scorecard,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2, default=str))
    print("VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_READY")
    print("TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
