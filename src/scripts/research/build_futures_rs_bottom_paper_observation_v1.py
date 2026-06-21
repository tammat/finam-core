#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import subprocess
import sys
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


ACTIVE_UNIVERSE_SCRIPT = "src/scripts/research/build_active_futures_universe_v1.py"

LOOKBACK_BARS = 12
AVG_VOLUME_BARS = 20
RANGE_BARS = 12
HORIZON_MIN = 240
HORIZON_BARS = 48

TARGET_SELECTIONS = {"BOTTOM1", "BOTTOM3"}
TARGET_FILTERS = {"COMPRESSION_RANGE", "REVERSAL_UP_CLOSE"}


def dec(v):
    return Decimal(str(v)) if v is not None else Decimal("0")


def pct(a, b):
    a = dec(a)
    b = dec(b)
    if a == 0:
        return None
    return (b - a) / a * Decimal("100")


def extract_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start < 0 or end < 0:
        raise RuntimeError("ACTIVE_UNIVERSE_JSON_NOT_FOUND")
    return json.loads(raw[start:end + 1])


def load_active_m5_symbols() -> list[dict]:
    env = os.environ.copy()
    env["PYTHONPATH"] = "src"
    env["RUNTIME_ALLOW_TRADING"] = "0"
    env["EXECUTION_ENABLED"] = "0"
    env["REAL_TRADING_ENABLED"] = "0"

    proc = subprocess.run(
        [sys.executable, ACTIVE_UNIVERSE_SCRIPT],
        cwd="/opt/finam-core",
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout)

    data = extract_json(proc.stdout)

    rows = []
    for r in data.get("rows", []):
        if (
            r.get("timeframe") == "M5"
            and r.get("quality") == "OK"
            and r.get("role") in {"PRIMARY_WATCH", "SECONDARY_WATCH"}
        ):
            rows.append({
                "symbol": r["symbol"],
                "family": r["family"],
                "timeframe": r["timeframe"],
                "role": r["role"],
            })

    return rows


def migrate(cur):
    cur.execute("""
        create table if not exists analytics_futures_rs_bottom_paper_observation_v1 (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            source_ts timestamptz not null,
            symbol text not null,
            family text,
            timeframe text not null default 'M5',
            role text,
            selection text not null,
            filter_name text not null,
            horizon_min integer not null default 240,
            source_close numeric not null,
            future_ts timestamptz,
            future_close numeric,
            return_pct numeric,
            status text not null,
            runtime_allow_trading text not null default '0',
            execution_enabled text not null default '0',
            real_trading_enabled text not null default '0',
            unique(source_ts, symbol, selection, filter_name, horizon_min)
        );
    """)

    cur.execute("""
        create index if not exists idx_futures_rs_bottom_paper_obs_v1_status
        on analytics_futures_rs_bottom_paper_observation_v1(status, source_ts desc);
    """)

    cur.execute("""
        create index if not exists idx_futures_rs_bottom_paper_obs_v1_symbol
        on analytics_futures_rs_bottom_paper_observation_v1(symbol, source_ts desc);
    """)


def upsert_signal(cur, row):
    cur.execute("""
        insert into analytics_futures_rs_bottom_paper_observation_v1 (
            source_ts, symbol, family, timeframe, role,
            selection, filter_name, horizon_min,
            source_close, future_ts, future_close, return_pct, status,
            runtime_allow_trading, execution_enabled, real_trading_enabled
        )
        values (
            %(source_ts)s, %(symbol)s, %(family)s, %(timeframe)s, %(role)s,
            %(selection)s, %(filter_name)s, %(horizon_min)s,
            %(source_close)s, %(future_ts)s, %(future_close)s, %(return_pct)s, %(status)s,
            '0', '0', '0'
        )
        on conflict (source_ts, symbol, selection, filter_name, horizon_min) do update set
            future_ts = excluded.future_ts,
            future_close = excluded.future_close,
            return_pct = excluded.return_pct,
            status = excluded.status,
            created_at = now()
    """, row)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    runtime_allow = os.getenv("RUNTIME_ALLOW_TRADING", "0")
    execution_enabled = os.getenv("EXECUTION_ENABLED", "0")
    real_trading_enabled = os.getenv("REAL_TRADING_ENABLED", "0")

    if runtime_allow != "0" or execution_enabled != "0" or real_trading_enabled != "0":
        raise SystemExit("SAFETY_FLAGS_NOT_ZERO")

    active = load_active_m5_symbols()
    inserted_or_updated = 0
    emitted_signals = 0
    waiting = 0
    success = 0
    failure = 0

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            migrate(cur)

            universe = {r["symbol"]: r for r in active}
            bars_by_symbol = {}

            for symbol in universe:
                cur.execute("""
                    select ts, open, high, low, close, volume
                    from market_bars
                    where symbol = %s
                      and timeframe = 'M5'
                      and close is not null
                      and close > 0
                    order by ts desc
                    limit 120
                """, (symbol,))
                bars = list(reversed(cur.fetchall()))
                if len(bars) >= max(LOOKBACK_BARS, AVG_VOLUME_BARS, RANGE_BARS) + 1:
                    bars_by_symbol[symbol] = bars

            latest_rows = []
            for symbol, bars in bars_by_symbol.items():
                i = len(bars) - 1
                rs = pct(bars[i - LOOKBACK_BARS]["close"], bars[i]["close"])
                if rs is None:
                    continue

                prev_close = dec(bars[i - 1]["close"])
                close = dec(bars[i]["close"])
                volume = dec(bars[i]["volume"])

                vol_window = [dec(x["volume"]) for x in bars[i - AVG_VOLUME_BARS:i] if x["volume"] is not None]
                avg_volume = sum(vol_window, Decimal("0")) / Decimal(len(vol_window)) if vol_window else Decimal("0")

                range_window = [
                    dec(x["high"]) - dec(x["low"])
                    for x in bars[i - RANGE_BARS:i]
                    if x["high"] is not None and x["low"] is not None
                ]
                avg_range = sum(range_window, Decimal("0")) / Decimal(len(range_window)) if range_window else Decimal("0")
                current_range = dec(bars[i]["high"]) - dec(bars[i]["low"])

                filters = set()
                if avg_range > 0 and current_range < avg_range * Decimal("0.70"):
                    filters.add("COMPRESSION_RANGE")
                if close > prev_close:
                    filters.add("REVERSAL_UP_CLOSE")

                latest_rows.append({
                    "symbol": symbol,
                    "family": universe[symbol]["family"],
                    "timeframe": "M5",
                    "role": universe[symbol]["role"],
                    "source_ts": bars[i]["ts"],
                    "source_close": close,
                    "rs_score": rs,
                    "filters": filters,
                })

            ranked = sorted(latest_rows, key=lambda r: r["rs_score"])

            for idx, r in enumerate(ranked, start=1):
                selections = []
                if idx == 1:
                    selections.append("BOTTOM1")
                if idx <= 3:
                    selections.append("BOTTOM3")

                for selection in selections:
                    if selection not in TARGET_SELECTIONS:
                        continue

                    for filter_name in sorted(r["filters"] & TARGET_FILTERS):
                        target_ts = r["source_ts"] + timedelta(minutes=HORIZON_MIN)

                        cur.execute("""
                            select ts, close
                            from market_bars
                            where symbol = %s
                              and timeframe = 'M5'
                              and ts >= %s
                              and close is not null
                              and close > 0
                            order by ts asc
                            limit 1
                        """, (r["symbol"], target_ts))
                        future = cur.fetchone()

                        future_ts = None
                        future_close = None
                        ret = None
                        status = "WAITING"

                        if future:
                            future_ts = future["ts"]
                            future_close = future["close"]
                            raw_ret = pct(r["source_close"], future_close)
                            ret = -raw_ret if raw_ret is not None else None
                            if ret is not None:
                                status = "SUCCESS" if ret > 0 else "FAILURE"

                        upsert_signal(cur, {
                            "source_ts": r["source_ts"],
                            "symbol": r["symbol"],
                            "family": r["family"],
                            "timeframe": r["timeframe"],
                            "role": r["role"],
                            "selection": selection,
                            "filter_name": filter_name,
                            "horizon_min": HORIZON_MIN,
                            "source_close": r["source_close"],
                            "future_ts": future_ts,
                            "future_close": future_close,
                            "return_pct": ret,
                            "status": status,
                        })

                        inserted_or_updated += 1
                        emitted_signals += 1
                        if status == "WAITING":
                            waiting += 1
                        elif status == "SUCCESS":
                            success += 1
                        elif status == "FAILURE":
                            failure += 1

            cur.execute("""
                select
                    count(*)::int as rows_total,
                    count(*) filter (where status='WAITING')::int as waiting,
                    count(*) filter (where status='SUCCESS')::int as success,
                    count(*) filter (where status='FAILURE')::int as failure
                from analytics_futures_rs_bottom_paper_observation_v1
            """)
            totals = cur.fetchone()

        conn.commit()

    print("=== FUTURES_RS_BOTTOM_PAPER_OBSERVATION_V1 ===")
    print("mode=paper_observation")
    print("db_update=1")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"runtime_allow_trading={runtime_allow}")
    print(f"execution_enabled={execution_enabled}")
    print(f"real_trading_enabled={real_trading_enabled}")
    print(f"active_symbols={len(active)}")
    print(f"ranked_symbols={len(latest_rows)}")
    print(f"signals_emitted={emitted_signals}")
    print(f"saved_rows={inserted_or_updated}")
    print(f"waiting={waiting}")
    print(f"success={success}")
    print(f"failure={failure}")
    print(f"rows_total={totals['rows_total']}")
    print(f"rows_waiting={totals['waiting']}")
    print(f"rows_success={totals['success']}")
    print(f"rows_failure={totals['failure']}")
    print("VERDICT=FUTURES_RS_BOTTOM_PAPER_OBSERVATION_READY")
    print("TEST_FUTURES_RS_BOTTOM_PAPER_OBSERVATION_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
