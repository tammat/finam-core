#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import json
import os
import subprocess
import sys
from collections import defaultdict
from decimal import Decimal

import psycopg
from psycopg.rows import dict_row


ACTIVE_UNIVERSE_SCRIPT = "src/scripts/research/build_active_futures_universe_v1.py"
LOOKBACK_BARS = 12
HORIZONS = {
    15: 3,
    60: 12,
    240: 48,
}


def dec(v) -> Decimal:
    if v is None:
        return Decimal("0")
    return Decimal(str(v))


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


def load_active_m5_symbols() -> list[str]:
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

    # Русский комментарий: для исторического RS используем только M5-контракты из активной вселенной.
    return sorted({
        r["symbol"]
        for r in data.get("rows", [])
        if r.get("timeframe") == "M5"
        and r.get("quality") == "OK"
        and r.get("role") in {"PRIMARY_WATCH", "SECONDARY_WATCH"}
    })


def migrate(cur) -> None:
    cur.execute("""
        create table if not exists analytics_futures_rs_historical_scorecard_v1 (
            id bigserial primary key,
            created_at timestamptz not null default now(),
            selection text not null,
            horizon_min integer not null,
            observations integer not null,
            wins integer not null,
            losses integer not null,
            winrate numeric,
            avg_return_pct numeric,
            gross_win_pct numeric,
            gross_loss_pct numeric,
            profit_factor numeric,
            unique(selection, horizon_min)
        );
    """)


def upsert_scorecard(cur, rows: list[dict]) -> None:
    for r in rows:
        cur.execute("""
            insert into analytics_futures_rs_historical_scorecard_v1 (
                selection, horizon_min, observations, wins, losses,
                winrate, avg_return_pct, gross_win_pct, gross_loss_pct, profit_factor
            )
            values (
                %(selection)s, %(horizon_min)s, %(observations)s, %(wins)s, %(losses)s,
                %(winrate)s, %(avg_return_pct)s, %(gross_win_pct)s, %(gross_loss_pct)s, %(profit_factor)s
            )
            on conflict (selection, horizon_min) do update set
                created_at = now(),
                observations = excluded.observations,
                wins = excluded.wins,
                losses = excluded.losses,
                winrate = excluded.winrate,
                avg_return_pct = excluded.avg_return_pct,
                gross_win_pct = excluded.gross_win_pct,
                gross_loss_pct = excluded.gross_loss_pct,
                profit_factor = excluded.profit_factor
        """, r)


def summarize(bucket: list[Decimal]) -> dict:
    obs = len(bucket)
    wins = sum(1 for x in bucket if x > 0)
    losses = sum(1 for x in bucket if x < 0)
    gross_win = sum((x for x in bucket if x > 0), Decimal("0"))
    gross_loss = abs(sum((x for x in bucket if x < 0), Decimal("0")))
    avg = sum(bucket, Decimal("0")) / Decimal(obs) if obs else None
    pf = gross_win / gross_loss if gross_loss else None

    return {
        "observations": obs,
        "wins": wins,
        "losses": losses,
        "winrate": wins / obs if obs else None,
        "avg_return_pct": avg,
        "gross_win_pct": gross_win,
        "gross_loss_pct": gross_loss,
        "profit_factor": pf,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--limit", type=int, default=2500)
    args = parser.parse_args()

    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    symbols = load_active_m5_symbols()
    if not symbols:
        raise SystemExit("ACTIVE_M5_SYMBOLS_EMPTY")

    by_ts = defaultdict(list)

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            if args.migrate:
                migrate(cur)

            for symbol in symbols:
                cur.execute("""
                    select ts, close
                    from market_bars
                    where symbol = %s
                      and timeframe = 'M5'
                      and close is not null
                      and close > 0
                    order by ts desc
                    limit %s
                """, (symbol, args.limit))
                bars = list(reversed(cur.fetchall()))

                for i in range(LOOKBACK_BARS, len(bars)):
                    rs = pct(bars[i - LOOKBACK_BARS]["close"], bars[i]["close"])
                    if rs is None:
                        continue

                    future = {}
                    for horizon_min, horizon_bars in HORIZONS.items():
                        j = i + horizon_bars
                        if j < len(bars):
                            future[horizon_min] = pct(bars[i]["close"], bars[j]["close"])

                    if future:
                        by_ts[bars[i]["ts"]].append({
                            "symbol": symbol,
                            "rs_score": rs,
                            "future": future,
                        })

            buckets = defaultdict(list)

            for ts, rows in by_ts.items():
                if len(rows) < 3:
                    continue

                ranked = sorted(rows, key=lambda r: r["rs_score"], reverse=True)

                for idx, r in enumerate(ranked, start=1):
                    total = len(ranked)
                    selections = []
                    if idx == 1:
                        selections.append("TOP1")
                    if idx <= 3:
                        selections.append("TOP3")
                    if idx == total:
                        selections.append("BOTTOM1")
                    if idx > max(total - 3, 0):
                        selections.append("BOTTOM3")

                    for horizon_min, ret in r["future"].items():
                        if ret is None:
                            continue

                        for sel in selections:
                            value = ret
                            # Русский комментарий: для нижней части рейтинга проверяем short-follow-through.
                            if sel.startswith("BOTTOM"):
                                value = -ret
                            buckets[(sel, horizon_min)].append(value)

            score_rows = []
            for (selection, horizon_min), values in sorted(buckets.items()):
                s = summarize(values)
                row = {
                    "selection": selection,
                    "horizon_min": horizon_min,
                    **s,
                }
                score_rows.append(row)

            if args.save:
                upsert_scorecard(cur, score_rows)

        conn.commit()

    print("=== FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_V1 ===")
    print(f"mode={'save' if args.save else 'read_only'}")
    print(f"db_update={1 if args.save else 0}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("telegram_send=0")
    print(f"active_symbols={len(symbols)}")
    print(f"timestamps={len(by_ts)}")
    print(f"scorecard_rows={len(score_rows)}")

    for r in score_rows:
        print(
            "FUTURES_RS_HIST_ROW "
            f"selection={r['selection']} "
            f"horizon_min={r['horizon_min']} "
            f"observations={r['observations']} "
            f"wins={r['wins']} "
            f"losses={r['losses']} "
            f"winrate={r['winrate']} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"profit_factor={r['profit_factor']}",
            flush=True,
        )

    print("VERDICT=FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_READY")
    print("TEST_FUTURES_RELATIVE_STRENGTH_HISTORICAL_SCORECARD_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
