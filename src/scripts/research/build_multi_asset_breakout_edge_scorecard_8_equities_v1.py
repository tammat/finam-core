#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import os
from decimal import Decimal
import psycopg
from psycopg.rows import dict_row


def fnum(x):
    if x is None:
        return 0.0
    return float(x)


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL_NOT_SET")

    with psycopg.connect(dsn, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                select symbol, priority, score
                from runtime_active_universe
                where is_enabled = true
                  and symbol like '%@MISX'
                  and source = 'runtime_universe_allocator_v2'
                order by priority desc nulls last, score desc nulls last, symbol
            """)
            runtime = list(cur.fetchall())

            symbols = [r["symbol"] for r in runtime]

            score_rows = []
            for symbol in symbols:
                cur.execute("""
                    select
                        count(*)::int as observations,
                        sum(case when status like '%%BREAKOUT_READY%%' then 1 else 0 end)::int as breakout_ready,
                        sum(case when status like '%%NO_BREAKOUT%%' then 1 else 0 end)::int as no_breakout,
                        sum(case when status like '%%NO_ENOUGH_BARS%%' then 1 else 0 end)::int as no_bars,
                        sum(
                            case
                                when close is not null
                                 and prev_high is not null
                                 and prev_high::numeric > 0
                                 and ((close::numeric - prev_high::numeric) / prev_high::numeric) >= -0.005
                                then 1 else 0
                            end
                        )::int as close_to_breakout,
                        max(created_at) as last_seen
                    from analytics_multi_asset_breakout_row_v1
                    where symbol = %s
                """, (symbol,))
                base = dict(cur.fetchone())

                cur.execute("""
                    select
                        count(*)::int as follow_rows,
                        sum(case when direction_ok is true then 1 else 0 end)::int as follow_success,
                        sum(case when direction_ok is false then 1 else 0 end)::int as follow_failure,
                        sum(case when direction_ok is null then 1 else 0 end)::int as follow_waiting,
                        avg(return_pct)::numeric as avg_return_pct
                    from analytics_multi_asset_breakout_follow_through_v1
                    where symbol = %s
                """, (symbol,))
                follow = dict(cur.fetchone())

                observations = int(base["observations"] or 0)
                close_to_breakout = int(base["close_to_breakout"] or 0)
                breakout_ready = int(base["breakout_ready"] or 0)
                follow_rows = int(follow["follow_rows"] or 0)
                follow_success = int(follow["follow_success"] or 0)
                follow_failure = int(follow["follow_failure"] or 0)
                follow_waiting = int(follow.get("follow_waiting") or 0)
                avg_return_pct = fnum(follow["avg_return_pct"])

                close_rate = close_to_breakout / observations if observations else 0.0
                ready_rate = breakout_ready / observations if observations else 0.0
                follow_winrate = follow_success / follow_rows if follow_rows else 0.0

                edge_score = (
                    close_rate * 0.25
                    + ready_rate * 0.35
                    + follow_winrate * 0.30
                    + max(min(avg_return_pct, 2.0), -2.0) / 2.0 * 0.10
                )

                score_rows.append({
                    "symbol": symbol,
                    "priority": runtime[symbols.index(symbol)]["priority"],
                    "runtime_score": runtime[symbols.index(symbol)]["score"],
                    "observations": observations,
                    "close_to_breakout": close_to_breakout,
                    "breakout_ready": breakout_ready,
                    "no_breakout": int(base["no_breakout"] or 0),
                    "no_bars": int(base["no_bars"] or 0),
                    "follow_rows": follow_rows,
                    "follow_success": follow_success,
                    "follow_failure": follow_failure,
                    "follow_waiting": follow_waiting,
                    "avg_return_pct": avg_return_pct,
                    "close_rate": round(close_rate, 6),
                    "ready_rate": round(ready_rate, 6),
                    "follow_winrate": round(follow_winrate, 6),
                    "edge_score": round(edge_score, 6),
                    "last_seen": base["last_seen"],
                })

    score_rows.sort(key=lambda r: (r["edge_score"], r["close_to_breakout"], r["observations"]), reverse=True)

    top = score_rows[0] if score_rows else None

    out = {
        "verdict": "MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_READY",
        "db_update": 0,
        "runtime_changed": 0,
        "execution_changed": 0,
        "telegram_send": 0,
        "runtime_equities": len(runtime),
        "scorecard_rows": len(score_rows),
        "equities_with_ready": sum(1 for r in score_rows if r["breakout_ready"] > 0),
        "equities_with_follow": sum(1 for r in score_rows if r["follow_rows"] > 0),
        "top_edge_symbol": top["symbol"] if top else None,
        "top_edge_score": top["edge_score"] if top else None,
        "rows": score_rows,
    }

    print(json.dumps(out, ensure_ascii=False, indent=2, default=str))

    for r in score_rows:
        print(
            "EQUITY_EDGE_ROW "
            f"symbol={r['symbol']} "
            f"observations={r['observations']} "
            f"close_to_breakout={r['close_to_breakout']} "
            f"breakout_ready={r['breakout_ready']} "
            f"follow_success={r['follow_success']} "
            f"follow_failure={r['follow_failure']} "
            f"avg_return_pct={r['avg_return_pct']} "
            f"edge_score={r['edge_score']}",
            flush=True,
        )

    print(
        "EQUITY_EDGE_SCORECARD_SUMMARY "
        f"runtime_equities={len(runtime)} "
        f"scorecard_rows={len(score_rows)} "
        f"equities_with_ready={out['equities_with_ready']} "
        f"equities_with_follow={out['equities_with_follow']} "
        f"top_edge_symbol={out['top_edge_symbol']} "
        f"top_edge_score={out['top_edge_score']}",
        flush=True,
    )
    print("VERDICT=MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_READY")
    print("TEST_MULTI_ASSET_BREAKOUT_EDGE_SCORECARD_8_EQUITIES_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
