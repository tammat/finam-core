#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import Bar, default_variants, evaluate_walk_forward, simulate_variant
from scripts.analytics.build_futures_risk_calibration_v1 import atr_at_entry

SUPPORTED = {
    "MEAN_REVERSION_EQUITY": "M5",
    "BR_CONSERVATIVE_BREAKOUT": "M5",
}


def main() -> int:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("select pg_advisory_xact_lock(hashtext('entry_exit_optimizer_v1'))")
        cur.execute("""
          SELECT id,symbol,strategy,upper(side) side,entry_price,exit_price,net_pnl,
                 coalesce(entry_ts,opened_at,created_at) entry_ts,
                 coalesce(closed_at,exit_ts,created_at) exit_ts
          FROM closed_trades
          WHERE trade_source='paper'
            AND coalesce(payload->'context'->>'cohort','') LIKE 'FRESH_V5%%'
            AND strategy=ANY(%s)
            AND coalesce(entry_ts,opened_at,created_at) IS NOT NULL
            AND coalesce(closed_at,exit_ts,created_at) IS NOT NULL
          ORDER BY coalesce(entry_ts,opened_at,created_at)
        """, (list(SUPPORTED),))
        groups = defaultdict(list)
        for trade in cur.fetchall():
            strategy, side = trade["strategy"], "LONG" if trade["side"] in {"LONG", "BUY"} else "SHORT"
            group = "BR" if strategy == "BR_CONSERVATIVE_BREAKOUT" else trade["symbol"].split("@", 1)[0]
            atr = atr_at_entry(cur, trade["symbol"], SUPPORTED[strategy], trade["entry_ts"])
            if not atr:
                continue
            cur.execute("""SELECT high::float8,low::float8,close::float8 FROM market_bars
                           WHERE symbol=%s AND timeframe=%s AND ts BETWEEN %s AND %s
                           ORDER BY ts""", (trade["symbol"], SUPPORTED[strategy], trade["entry_ts"], trade["exit_ts"]))
            bars = [Bar(float(r["high"]),float(r["low"]),float(r["close"])) for r in cur.fetchall()]
            if not bars:
                continue
            groups[(strategy,group,side)].append((trade,float(atr),bars))

        for (strategy,group,side), trades in groups.items():
            for variant in default_variants(strategy):
                rows = []
                for trade,atr,bars in trades:
                    direction = 1 if side == "LONG" else -1
                    risk = atr * variant.stop_atr
                    actual_r = direction * (float(trade["exit_price"])-float(trade["entry_price"])) / risk
                    outcome = simulate_variant(signal_price=float(trade["entry_price"]), side=side, atr=atr,
                                               bars=bars, variant=variant)
                    rows.append({"actual_r":actual_r,"shadow_r":outcome.net_r})
                    cur.execute("""INSERT INTO analytics.entry_exit_shadow_pair_v1
                      (trade_id,strategy_code,symbol_code,side_code,candidate_code,entry_mode,stop_atr,take_atr,
                       trail_after_r,trail_atr,actual_net_r,shadow_entered,shadow_net_r,shadow_exit_reason)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(trade_id,candidate_code) DO UPDATE SET
                       actual_net_r=excluded.actual_net_r,shadow_entered=excluded.shadow_entered,
                       shadow_net_r=excluded.shadow_net_r,shadow_exit_reason=excluded.shadow_exit_reason,
                       generated_at=clock_timestamp()""",
                      (trade["id"],strategy,trade["symbol"],side,variant.code,variant.entry_mode,
                       variant.stop_atr,variant.take_atr,variant.trail_after_r,variant.trail_atr,
                       actual_r,outcome.entered,outcome.net_r,outcome.reason))
                metrics = evaluate_walk_forward(rows)
                oos = int(metrics.get("oos_pairs") or 0)
                if oos:
                    ids = [int(item[0]["id"]) for item in trades[-oos:]]
                    cur.execute("""UPDATE analytics.entry_exit_shadow_pair_v1 SET is_oos=true
                                   WHERE candidate_code=%s AND trade_id=ANY(%s)""", (variant.code,ids))
                cur.execute("""INSERT INTO analytics.entry_exit_recommendation_v1
                  (strategy_code,symbol_group,side_code,candidate_code,recommendation_status,pairs,oos_pairs,
                   entry_mode,stop_atr,take_atr,trail_after_r,trail_atr,metrics)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                  ON CONFLICT(strategy_code,symbol_group,side_code,candidate_code) DO UPDATE SET
                   recommendation_status=excluded.recommendation_status,pairs=excluded.pairs,oos_pairs=excluded.oos_pairs,
                   metrics=excluded.metrics,generated_at=clock_timestamp()""",
                  (strategy,group,side,variant.code,metrics["status"],metrics["pairs"],oos,
                   variant.entry_mode,variant.stop_atr,variant.take_atr,variant.trail_after_r,variant.trail_atr,
                   json.dumps(metrics)))
                print("ENTRY_EXIT_SHADOW",strategy,group,side,variant.code,json.dumps(metrics,sort_keys=True))
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
