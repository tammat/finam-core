#!/usr/bin/env python3
from __future__ import annotations

import json
import os
from collections import defaultdict

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    Bar, default_variants, evaluate_active_paper_champion, evaluate_paper_challenger,
    evaluate_walk_forward, simulate_variant,
)
from scripts.analytics.build_futures_risk_calibration_v1 import atr_at_entry

SUPPORTED = {
    "MEAN_REVERSION_EQUITY": "M5",
    "VOLATILITY_BREAKOUT_EQUITY": "M5",
    "BR_CONSERVATIVE_BREAKOUT": "M5",
    "NG_CONSERVATIVE_BREAKOUT_M1": "M1",
    "CNY_REGIME_FUTURES": "M1",
}

# Independent candidate horizon.  It is intentionally defined in completed
# bars and never inherited from the incumbent Paper trade's exit timestamp.
SHADOW_HORIZON_BARS = {
    "MEAN_REVERSION_EQUITY": 48,       # four hours on M5
    "VOLATILITY_BREAKOUT_EQUITY": 72,  # six hours on M5
    "BR_CONSERVATIVE_BREAKOUT": 72,    # six hours on M5
    "NG_CONSERVATIVE_BREAKOUT_M1": 180,
    "CNY_REGIME_FUTURES": 180,
}


def execution_economics(cursor, trade: dict) -> dict | None:
    """Return fail-closed cash/price conversion and conservative costs."""
    symbol = str(trade["symbol"])
    qty = abs(float(trade.get("qty") or 0.0))
    if qty <= 0:
        return None
    is_futures = symbol.upper().endswith("@RTSX")
    multiplier = 1.0
    tick = 0.0
    if is_futures:
        cursor.execute("""SELECT tick_size::float8,tick_value::float8
                          FROM analytics.market_contract_spec_v1
                          WHERE symbol=%s AND is_active
                          ORDER BY valid_from DESC LIMIT 1""", (symbol,))
        spec = cursor.fetchone()
        tick = float(spec["tick_size"] or 0.0) if spec else 0.0
        tick_value = float(spec["tick_value"] or 0.0) if spec else 0.0
        if tick <= 0 or tick_value <= 0:
            return None
        multiplier = tick_value / tick
    commission_rub = max(0.0, float(trade.get("commission") or 0.0))
    observed_cost_price = commission_rub / (qty * multiplier)
    # Never simulate frictionless fills.  Futures pay at least one adverse tick
    # per side; equities use a configurable conservative round-trip bps floor.
    floor_price = (2.0 * tick if is_futures else
                   float(trade["entry_price"]) *
                   float(os.getenv("SHADOW_EQUITY_ROUNDTRIP_COST_BPS", "8")) / 10_000.0)
    return {
        "qty": qty, "multiplier": multiplier, "tick_size": tick,
        "roundtrip_cost_price": max(observed_cost_price, floor_price),
        "contract_spec_ok": not is_futures or (tick > 0 and multiplier > 0),
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
          SELECT id,symbol,strategy,upper(side) side,qty,entry_price,exit_price,
                 gross_pnl,commission,net_pnl,
                 coalesce(entry_ts,opened_at,created_at) entry_ts,
                 coalesce(closed_at,exit_ts,created_at) exit_ts,
                 coalesce(payload->'context'->>'regime_trend',
                          payload->'context'->>'regime',
                          payload->>'regime','UNKNOWN') regime
          FROM closed_trades
          WHERE trade_source='paper'
            AND coalesce(payload->'context'->>'cohort','') LIKE 'FRESH_V5%%'
            AND payload->'pnl_units'->>'version'='PNL_UNITS_V2_RUB'
            AND strategy=ANY(%s)
            AND coalesce(entry_ts,opened_at,created_at) IS NOT NULL
            AND coalesce(closed_at,exit_ts,created_at) IS NOT NULL
          ORDER BY coalesce(entry_ts,opened_at,created_at)
        """, (list(SUPPORTED),))
        groups = defaultdict(list)
        independent_signals = set()
        for trade in cur.fetchall():
            strategy, side = trade["strategy"], "LONG" if trade["side"] in {"LONG", "BUY"} else "SHORT"
            group = symbol_group(strategy, trade["symbol"])
            bucket = trade["entry_ts"].replace(minute=(trade["entry_ts"].minute // 30) * 30,
                                                second=0, microsecond=0)
            independent_key = (strategy, group, side, bucket)
            if independent_key in independent_signals:
                continue
            atr = atr_at_entry(cur, trade["symbol"], SUPPORTED[strategy], trade["entry_ts"])
            if not atr:
                continue
            economics = execution_economics(cur, trade)
            if not economics:
                continue
            cur.execute("""SELECT open::float8,high::float8,low::float8,close::float8 FROM market_bars
                           WHERE symbol=%s AND timeframe=%s AND ts > %s
                           ORDER BY ts LIMIT %s""",
                        (trade["symbol"], SUPPORTED[strategy], trade["entry_ts"],
                         SHADOW_HORIZON_BARS[strategy]))
            bars = [Bar(float(r["high"]),float(r["low"]),float(r["close"]),float(r["open"]))
                    for r in cur.fetchall()]
            # A partially observed horizon is allowed for accumulation but can
            # never enter selection/promotion statistics.
            horizon_complete = len(bars) == SHADOW_HORIZON_BARS[strategy]
            if not bars:
                continue
            independent_signals.add(independent_key)
            groups[(strategy,group,side)].append((trade,float(atr),bars,economics,horizon_complete))

        for (strategy,group,side), trades in groups.items():
            candidate_results = []
            for variant in default_variants(strategy):
                rows = []
                for trade,atr,bars,economics,horizon_complete in trades:
                    risk = atr * variant.stop_atr
                    cash_risk = risk * economics["qty"] * economics["multiplier"]
                    actual_r = float(trade["net_pnl"]) / cash_risk
                    outcome = simulate_variant(signal_price=float(trade["entry_price"]), side=side, atr=atr,
                                               bars=bars, variant=variant,
                                               roundtrip_cost_price=economics["roundtrip_cost_price"],
                                               tick_size=economics["tick_size"],
                                               stop_slippage_ticks=float(os.getenv(
                                                   "SHADOW_STOP_SLIPPAGE_TICKS", "1")))
                    rows.append({"actual_r":actual_r,
                                 "shadow_r":outcome.net_r if horizon_complete else None,
                                 "shadow_observed_r": outcome.net_r,
                                 "horizon_complete": horizon_complete,
                                 "trade_date":trade["entry_ts"].date().isoformat(),
                                 "regime":str(trade.get("regime") or "UNKNOWN")})
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
                       actual_r,outcome.entered,outcome.net_r if horizon_complete else None,
                       outcome.reason if horizon_complete else "PARTIAL_INDEPENDENT_HORIZON"))
                metrics = evaluate_walk_forward(rows)
                candidate_results.append((variant, metrics, rows))
                oos = int(metrics.get("oos_pairs") or 0)
                all_ids = [int(item[0]["id"]) for item in trades]
                if all_ids:
                    cur.execute("""UPDATE analytics.entry_exit_shadow_pair_v1 SET is_oos=false
                                   WHERE candidate_code=%s AND trade_id=ANY(%s)""",
                                (variant.code, all_ids))
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

            cur.execute("""SELECT c.*,p.candidate_code AS active_candidate_code,p.profile_id AS active_profile_id,
                                  p.activated_at AS active_activated_at
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
            active_activated_at = state["active_activated_at"] if state else None
            champion_metrics = dict(state["champion_metrics"] or {}) if state else {}
            degraded_cycles = int(state["consecutive_degraded_cycles"] or 0) if state else 0
            rollback_reason = state["rollback_reason"] if state else None
            last_transition_at = state["last_transition_at"] if state else None

            if existing_code and active_code == existing_code:
                selected = by_code.get(existing_code)
                shadow_metrics = selected[1] if selected else (state["shadow_metrics"] or {})
                paper_metrics = state["paper_metrics"] or {}
                stage = "CHAMPION_ACTIVE"
                if selected and active_activated_at:
                    champion_rows = [row for row, trade_bundle in zip(selected[2], trades)
                                     if trade_bundle[0]["exit_ts"] >= active_activated_at]
                    validated_dd = max(
                        float(paper_metrics.get("challenger_drawdown_r") or 0),
                        float(shadow_metrics.get("shadow_drawdown_r") or 0), 0.01)
                    champion_metrics = evaluate_active_paper_champion(champion_rows, validated_dd)
                    health = champion_metrics["status"]
                    from datetime import date
                    evaluation_date = date.today().isoformat()
                    previous_evaluation_date = str(
                        (state.get("champion_metrics") or {}).get("evaluation_date") or ""
                    )
                    champion_metrics["evaluation_date"] = evaluation_date
                    if health == "DEGRADED" and previous_evaluation_date != evaluation_date:
                        degraded_cycles += 1
                    elif health != "DEGRADED":
                        degraded_cycles = 0
                    must_rollback = health == "ROLLBACK_NOW" or degraded_cycles >= 2
                    if must_rollback:
                        rollback_reason = champion_metrics["reason"]
                        cur.execute("""UPDATE analytics.entry_exit_runtime_profile_v1
                            SET status='ROLLED_BACK',deactivated_at=clock_timestamp()
                            WHERE profile_id=%s AND execution_mode='paper' AND status='ACTIVE'""",
                            (active_profile_id,))
                        cur.execute("""UPDATE analytics.entry_exit_runtime_profile_v1 SET status='ACTIVE',
                                      deactivated_at=NULL,activated_at=clock_timestamp(),
                                      activated_by='AUTO_ROLLBACK'
                            WHERE profile_id=(SELECT profile_id FROM analytics.entry_exit_runtime_profile_v1
                              WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                                AND execution_mode='paper' AND status='SUPERSEDED'
                              ORDER BY deactivated_at DESC NULLS LAST LIMIT 1)
                            RETURNING profile_id,candidate_code""", (strategy,group,side))
                        restored = cur.fetchone()
                        active_profile_id = restored["profile_id"] if restored else None
                        active_code = restored["candidate_code"] if restored else ""
                        stage = "ROLLED_BACK"
                        last_transition_at = "NOW"
                    elif health in {"HEALTHY", "MONITOR"}:
                        fresh_ready = []
                        for item in candidate_results:
                            if item[0].code == active_code or item[0].entry_mode != "IMMEDIATE":
                                continue
                            fresh_rows = [row for row, trade_bundle in zip(item[2], trades)
                                          if trade_bundle[0]["exit_ts"] >= active_activated_at]
                            metrics = evaluate_walk_forward(fresh_rows)
                            if metrics.get("status") == "READY_FOR_PAPER_CONFIRMATION":
                                fresh_ready.append((item, metrics))
                        fresh_ready.sort(key=lambda pair: (
                            float(pair[1].get("shadow_oos_r") or -999),
                            float(pair[1].get("shadow_expectancy_r") or -999)), reverse=True)
                        if fresh_ready:
                            selected, shadow_metrics = fresh_ready[0][0], fresh_ready[0][1]
                            existing_code = selected[0].code
                            selected_at = None
                            paper_metrics = {"status":"PAPER_CHALLENGER","pairs":0,"oos_pairs":0,
                                             "reason":"fresh adaptive candidate selected automatically"}
                            stage = "PAPER_CHALLENGER"
                            rollback_reason = None
            elif existing_code and existing_stage in {
                "PAPER_CHALLENGER", "KEEP_PAPER_CHALLENGER", "READY_FOR_CHAMPION_CONFIRMATION"
            } and existing_code in by_code and selected_at:
                selected = by_code[existing_code]
                forward_rows = [row for row, trade_bundle in zip(selected[2], trades)
                                if trade_bundle[0]["exit_ts"] >= selected_at]
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

            # Paper is an isolated learning contour: once every historical and
            # fresh forward guard has passed, promote the challenger without an
            # operator click. REAL is not represented by this table or job.
            auto_promotion_enabled = os.getenv("ENTRY_EXIT_AUTO_PROMOTION_ENABLED", "0") == "1"
            if stage == "READY_FOR_CHAMPION_CONFIRMATION" and not auto_promotion_enabled:
                stage = "PAPER_PROMOTION_BLOCKED_METHODOLOGY_GATE"
                paper_metrics = dict(paper_metrics)
                paper_metrics["promotion_blocked"] = True
                paper_metrics["promotion_block_reason"] = "ENTRY_EXIT_AUTO_PROMOTION_ENABLED=0"
            if stage == "READY_FOR_CHAMPION_CONFIRMATION" and auto_promotion_enabled:
                cur.execute("""UPDATE analytics.entry_exit_runtime_profile_v1
                    SET status='SUPERSEDED',deactivated_at=clock_timestamp()
                    WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                      AND execution_mode='paper' AND status='ACTIVE'""", (strategy,group,side))
                cur.execute("""INSERT INTO analytics.entry_exit_runtime_profile_v1
                    (strategy_code,symbol_group,side_code,candidate_code,status,entry_mode,
                     stop_atr,take_atr,trail_after_r,trail_atr,source_metrics,activated_by)
                    VALUES(%s,%s,%s,%s,'ACTIVE',%s,%s,%s,%s,%s,%s::jsonb,
                           'AUTO_CHAMPION_CHALLENGER') RETURNING profile_id""",
                    (strategy,group,side,selected[0].code,selected[0].entry_mode,
                     selected[0].stop_atr,selected[0].take_atr,selected[0].trail_after_r,
                     selected[0].trail_atr,json.dumps({
                         "shadow": shadow_metrics, "paper_forward": paper_metrics,
                         "promotion": "AUTO_PAPER_ONLY",
                     })))
                active_profile_id = cur.fetchone()["profile_id"]
                active_code = selected[0].code
                existing_code = active_code
                paper_metrics = dict(paper_metrics)
                paper_metrics["promoted_automatically"] = True
                paper_metrics["active_profile_id"] = active_profile_id
                stage = "CHAMPION_ACTIVE"
                champion_metrics = {}
                degraded_cycles = 0
                rollback_reason = None
                last_transition_at = "NOW"

            cur.execute("""INSERT INTO analytics.entry_exit_champion_challenger_v1
              (strategy_code,symbol_group,side_code,champion_profile_id,champion_candidate_code,
               challenger_candidate_code,challenger_status,challenger_selected_at,
               shadow_metrics,paper_metrics,auto_selected,champion_metrics,
               consecutive_degraded_cycles,rollback_reason,last_transition_at)
              VALUES(%s,%s,%s,%s,%s,%s,%s,
                     CASE WHEN %s='PAPER_CHALLENGER' THEN clock_timestamp() ELSE %s END,
                     %s::jsonb,%s::jsonb,%s,%s::jsonb,%s,%s,
                     CASE WHEN %s='NOW' THEN clock_timestamp() ELSE %s END)
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
               auto_selected=excluded.auto_selected,champion_metrics=excluded.champion_metrics,
               consecutive_degraded_cycles=excluded.consecutive_degraded_cycles,
               rollback_reason=excluded.rollback_reason,
               last_transition_at=excluded.last_transition_at,updated_at=clock_timestamp()""",
              (strategy,group,side,active_profile_id,active_code or "CURRENT_PAPER",
               existing_code,stage,stage,selected_at,json.dumps(shadow_metrics),
               json.dumps(paper_metrics),stage != "SHADOW_ACCUMULATION",json.dumps(champion_metrics),
               degraded_cycles,rollback_reason,last_transition_at,last_transition_at))
            print("ENTRY_EXIT_CHALLENGER",strategy,group,side,existing_code,stage,
                  json.dumps(paper_metrics,sort_keys=True))
        conn.commit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
