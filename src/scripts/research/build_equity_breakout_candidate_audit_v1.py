#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
import sys
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras


def to_float(value: Any):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except Exception:
        return None


def verdict_for(distance_pct, atr_ok, volume_ok, status):
    # Диагноз по близости акции к пробою.
    if status and "NO_ENOUGH_BARS" in status:
        return "NO_ENOUGH_BARS"
    if distance_pct is None:
        return "NO_PRICE_DATA"
    if distance_pct >= 0 and atr_ok and volume_ok:
        return "BREAKOUT_READY"
    if distance_pct >= -0.25:
        return "CLOSE_TO_BREAKOUT"
    if distance_pct >= -0.50:
        return "WATCH"
    return "FAR_FROM_BREAKOUT"


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")
    if not dsn:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 1

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                with latest as (
                    select distinct on (symbol, timeframe)
                        symbol,
                        asset_class,
                        timeframe,
                        role,
                        created_at,
                        bar_ts,
                        close,
                        prev_high,
                        breakout_ok,
                        atr_pct,
                        atr_min_pct,
                        atr_ok,
                        volume,
                        avg_volume,
                        volume_ratio,
                        volume_mult,
                        volume_ok,
                        status
                    from analytics_multi_asset_breakout_row_v1
                    where asset_class = 'EQUITY'
                      and timeframe = 'M5'
                    order by symbol, timeframe, created_at desc
                )
                select *
                from latest
                order by symbol
                """
            )
            rows = cur.fetchall()

    out_rows = []
    counts = {}

    for r in rows:
        close = to_float(r.get("close"))
        prev_high = to_float(r.get("prev_high"))
        distance_pct = None

        if close is not None and prev_high not in (None, 0):
            distance_pct = ((close - prev_high) / prev_high) * 100.0

        status = r.get("status") or ""
        v = verdict_for(
            distance_pct,
            bool(r.get("atr_ok")),
            bool(r.get("volume_ok")),
            status,
        )
        counts[v] = counts.get(v, 0) + 1

        out_rows.append(
            {
                "symbol": r.get("symbol"),
                "timeframe": r.get("timeframe"),
                "role": r.get("role"),
                "created_at": str(r.get("created_at")),
                "bar_ts": r.get("bar_ts"),
                "close": close,
                "prev_high": prev_high,
                "distance_to_breakout_pct": distance_pct,
                "breakout_ok": bool(r.get("breakout_ok")),
                "atr_pct": to_float(r.get("atr_pct")),
                "atr_min_pct": to_float(r.get("atr_min_pct")),
                "atr_ok": bool(r.get("atr_ok")),
                "volume_ratio": to_float(r.get("volume_ratio")),
                "volume_mult": to_float(r.get("volume_mult")),
                "volume_ok": bool(r.get("volume_ok")),
                "status": status,
                "audit_verdict": v,
            }
        )

    result = {
        "verdict": "EQUITY_BREAKOUT_CANDIDATE_AUDIT_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "equities_total": len(out_rows),
        "breakout_ready": counts.get("BREAKOUT_READY", 0),
        "close_to_breakout": counts.get("CLOSE_TO_BREAKOUT", 0),
        "watch": counts.get("WATCH", 0),
        "far_from_breakout": counts.get("FAR_FROM_BREAKOUT", 0),
        "no_enough_bars": counts.get("NO_ENOUGH_BARS", 0),
        "no_price_data": counts.get("NO_PRICE_DATA", 0),
        "rows": out_rows,
    }

    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("VERDICT=EQUITY_BREAKOUT_CANDIDATE_AUDIT_READY")
    print("TEST_EQUITY_BREAKOUT_CANDIDATE_AUDIT_V1_OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
