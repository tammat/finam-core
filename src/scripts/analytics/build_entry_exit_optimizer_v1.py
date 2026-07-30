#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    Bar, default_variants, evaluate_paper_challenger, evaluate_walk_forward, simulate_variant,
)
from scripts.analytics.build_futures_risk_calibration_v1 import atr_at_entry

SUPPORTED = {
    "MEAN_REVERSION_EQUITY": "M5",
    "VOLATILITY_BREAKOUT_EQUITY": "M5",
    "BR_CONSERVATIVE_BREAKOUT": "M5",
    "NG_CONSERVATIVE_BREAKOUT_M1": "M1",
    "CNY_REGIME_FUTURES": "M1",
}


def symbol_group(strategy: str, symbol: str) -> str:
    if strategy == "BR_CONSERVATIVE_BREAKOUT":
        return "BR"
    if strategy == "NG_CONSERVATIVE_BREAKOUT_M1":
        return "NG"
    if strategy == "CNY_REGIME_FUTURES":
        return "CNY"
    return symbol.split("@", 1)[0]


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
            group = symbol_group(strategy, trade["symbol"])
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
            candidate_results = []
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
                candidate_results.append((variant, metrics, rows))
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

            cur.execute("""SELECT c.*,p.candidate_code AS active_candidate_code,p.profile_id AS active_profile_id
                           FROM analytics.entry_exit_champion_challenger_v1 c
                           LEFT JOIN analytics.entry_exit_runtime_profile_v1 p
                             ON p.strategy_code=c.strategy_code AND p.symbol_group=c.symbol_group
                            AND p.side_code=c.side_code AND p.execution_mode='paper' AND p.status='ACTIVE'
                           WHERE c.strategy_code=%s AND c.symbol_group=%s AND c.side_code=%s""",
                        (strategy,group,side))
            state = cur.fetchone()
            ready = [item for item in candidate_results
                     if item[0].entry_mode == "IMMEDIATE"
                     and item[1].get("status") == "READY_FOR_PAPER_CONFIRMATION"]
            ready.sort(key=lambda item: (
                float(item[1].get("shadow_oos_r") or -999),
                float(item[1].get("shadow_expectancy_r") or -999),
                -float(item[1].get("shadow_drawdown_r") or 999),
            ), reverse=True)
            by_code = {item[0].code: item for item in candidate_results}
            existing_code = str(state["challenger_candidate_code"] or "") if state else ""
            existing_stage = str(state["challenger_status"] or "") if state else ""
            selected_at = state["challenger_selected_at"] if state else None
            active_code = str(state["active_candidate_code"] or "") if state else ""
            active_profile_id = state["active_profile_id"] if state else None

            if existing_code and active_code == existing_code:
                selected = by_code.get(existing_code)
                shadow_metrics = selected[1] if selected else (state["shadow_metrics"] or {})
                paper_metrics = state["paper_metrics"] or {}
                stage = "CHAMPION_ACTIVE"
            elif existing_code and existing_stage in {
                "PAPER_CHALLENGER", "KEEP_PAPER_CHALLENGER", "READY_FOR_CHAMPION_CONFIRMATION"
            } and existing_code in by_code and selected_at:
                selected = by_code[existing_code]
                forward_rows = [row for row, trade in zip(selected[2], trades)
                                if trade["exit_ts"] >= selected_at]
                paper_metrics = evaluate_paper_challenger(forward_rows)
                shadow_metrics = selected[1]
                stage = paper_metrics["status"]
            elif existing_code and existing_stage in {"ROLLED_BACK", "REJECTED"} and (
                not ready or ready[0][0].code == existing_code
            ):
                selected = by_code.get(existing_code)
                shadow_metrics = selected[1] if selected else (state["shadow_metrics"] or {})
                paper_metrics = state["paper_metrics"] or {}
                stage = existing_stage
            elif ready:
                selected = ready[0]
                existing_code = selected[0].code
                selected_at = None
                shadow_metrics = selected[1]
                paper_metrics = {"status":"PAPER_CHALLENGER","pairs":0,"oos_pairs":0,
                                 "reason":"forward comparison starts after automatic selection"}
                stage = "PAPER_CHALLENGER"
            else:
                observed = max(candidate_results, key=lambda item: (
                    int(item[1].get("pairs") or 0),
                    float(item[1].get("shadow_expectancy_r") or -999),
                ))
                existing_code = observed[0].code
                selected_at = None
                shadow_metrics = observed[1]
                paper_metrics = {}
                stage = "SHADOW_ACCUMULATION"

            cur.execute("""INSERT INTO analytics.entry_exit_champion_challenger_v1
              (strategy_code,symbol_group,side_code,champion_profile_id,champion_candidate_code,
               challenger_candidate_code,challenger_status,challenger_selected_at,
               shadow_metrics,paper_metrics,auto_selected)
              VALUES(%s,%s,%s,%s,%s,%s,%s,
                     CASE WHEN %s='PAPER_CHALLENGER' THEN clock_timestamp() ELSE %s END,
                     %s::jsonb,%s::jsonb,%s)
              ON CONFLICT(strategy_code,symbol_group,side_code) DO UPDATE SET
               champion_profile_id=excluded.champion_profile_id,
               champion_candidate_code=excluded.champion_candidate_code,
               challenger_candidate_code=excluded.challenger_candidate_code,
               challenger_status=excluded.challenger_status,
               challenger_selected_at=CASE
                 WHEN analytics.entry_exit_champion_challenger_v1.challenger_candidate_code
                      IS DISTINCT FROM excluded.challenger_candidate_code
                   THEN excluded.challenger_selected_at
                 ELSE coalesce(analytics.entry_exit_champion_challenger_v1.challenger_selected_at,
                               excluded.challenger_selected_at) END,
               shadow_metrics=excluded.shadow_metrics,paper_metrics=excluded.paper_metrics,
               auto_selected=excluded.auto_selected,updated_at=clock_timestamp()""",
              (strategy,group,side,active_profile_id,active_code or "CURRENT_PAPER",
               existing_code,stage,stage,selected_at,json.dumps(shadow_metrics),
               json.dumps(paper_metrics),stage != "SHADOW_ACCUMULATION"))
            print("ENTRY_EXIT_CHALLENGER",strategy,group,side,existing_code,stage,
                  json.dumps(paper_metrics,sort_keys=True))
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
