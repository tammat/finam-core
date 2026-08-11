#!/usr/bin/env python3
from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from marketcore.research.economics.economic_cost_gate_policy_loader_v1 import (
    load_economic_cost_gate_policy_v1,
)
from marketcore.research.economics.verified_net_admission_v1 import (
    build_verified_net_metrics_v1,
    evaluate_verified_net_admission_v1,
)


import json
import os
import random
import uuid
import hashlib
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from statistics import median

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.entry_exit_optimizer import (
    Bar, EntryContext, Variant, default_variants, expert_shadow_variants,
    candidate_futility_gate, candidate_statistical_gate,
    evaluate_active_paper_champion, evaluate_paper_challenger,
    evaluate_walk_forward, parameter_plateau_check, simulate_variant,
)
from finam_core.research.purged_split import purged_temporal_split
from scripts.analytics.build_futures_risk_calibration_v1 import atr_at_entry, timeframe_delta

SUPPORTED = {
    "MEAN_REVERSION_EQUITY": "M5",
    "VOLATILITY_BREAKOUT_EQUITY": "M5",
    "BR_CONSERVATIVE_BREAKOUT": "M5",
    "NG_CONSERVATIVE_BREAKOUT_M1": "M1",
    "CNY_REGIME_FUTURES": "M1",
    "USD_REGIME_FUTURES": "M1",
    "GOLD_TREND_BREAKOUT": "M1",
}

# Independent candidate horizon.  It is intentionally defined in completed
# bars and never inherited from the incumbent Paper trade's exit timestamp.
SHADOW_HORIZON_BARS = {
    "MEAN_REVERSION_EQUITY": 48,       # four hours on M5
    "VOLATILITY_BREAKOUT_EQUITY": 72,  # six hours on M5
    "BR_CONSERVATIVE_BREAKOUT": 72,    # six hours on M5
    "NG_CONSERVATIVE_BREAKOUT_M1": 180,
    "CNY_REGIME_FUTURES": 180,
    "USD_REGIME_FUTURES": 180,
    "GOLD_TREND_BREAKOUT": 240,
}

GENERIC_PAPER_RUNTIME_GROUPS = {"GAZP", "LKOH", "NVTK", "SBER", "SBERP", "VTBR"}


def placebo_entry_offsets(*, bars_count: int, source_id: int, candidate_code: str,
                          candidate_delay_bars: int, samples: int = 20) -> list[int]:
    """Build reproducible time-shift controls distinct from candidate entry."""
    offsets = [offset for offset in range(1, bars_count - 1)
               if offset != max(1, int(candidate_delay_bars or 0))]
    seed = int.from_bytes(hashlib.sha256(
        f"{source_id}:{candidate_code}:PLACEBO_TIME_SHIFT_V2".encode()).digest()[:8], "big")
    random.Random(seed).shuffle(offsets)
    return sorted(offsets[:max(1, samples)])


def paper_runtime_supported(group: str, entry_mode: str) -> bool:
    # Futures use their contract-aware calibrator until one unified risk object
    # owns both sizing and adaptive stop geometry.
    return group in GENERIC_PAPER_RUNTIME_GROUPS and entry_mode in {"IMMEDIATE", "ADAPTIVE"}


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
    if strategy == "USD_REGIME_FUTURES":
        return "USD"
    if strategy == "GOLD_TREND_BREAKOUT":
        return "GOLD"
    return symbol.split("@", 1)[0]


def research_family(strategy: str) -> str:
    if strategy in {"MEAN_REVERSION_EQUITY", "VOLATILITY_BREAKOUT_EQUITY"}:
        return "EQUITIES"
    if strategy == "BR_CONSERVATIVE_BREAKOUT":
        return "OIL"
    if strategy == "NG_CONSERVATIVE_BREAKOUT_M1":
        return "GAS"
    if strategy in {"CNY_REGIME_FUTURES", "USD_REGIME_FUTURES"}:
        return "FX"
    if strategy == "GOLD_TREND_BREAKOUT":
        return "METALS"
    return "OTHER"


def ensure_frozen_entry_exit_oos(cursor, *, strategy: str, symbol: str, side: str,
                                 variant: Variant, rows: list[dict],
                                 timeframe: str) -> str | None:
    """Pre-register one immutable future-only V5 run for an exact candidate."""
    cursor.execute("""SELECT coalesce(bool_or(enabled),false) locked
        FROM analytics.v5_program_lock_v1
        WHERE lock_code='CURRENT_V5_FOUR_BRANCHES_ONLY'""")
    if cursor.fetchone()["locked"]:
        cursor.execute("""SELECT admission_id
            FROM analytics.v5_post_fix_branch_registry_v1
            WHERE observation_symbol=%s AND strategy_code=%s AND side_code=%s
              AND candidate_code=%s LIMIT 1""", (symbol,strategy,side,variant.code))
        allowed = cursor.fetchone()
        if not allowed:
            return None
        return str(allowed["admission_id"])
    completed = [row for row in rows if row.get("shadow_r") is not None]
    if not completed:
        return None
    cursor.execute("""SELECT a.admission_id
        FROM analytics.trade_outcome_oos_admission_v1 a
        WHERE a.oos_request->>'observation_source'='ENTRY_EXIT_SHADOW_V2'
          AND a.symbol=%s AND a.oos_request->>'paper_strategy_code'=%s
          AND upper(a.oos_request->>'side_code')=%s
          AND a.oos_request->'frozen_profile'->>'candidate_code'=%s
          AND a.status_code IN ('QUEUED','RUNNING','OOS_PASS','OOS_FAIL')
        ORDER BY a.created_at DESC LIMIT 1""", (symbol,strategy,side,variant.code))
    existing = cursor.fetchone()
    if existing:
        return str(existing["admission_id"])
    cursor.execute("""SELECT run_id FROM analytics.trade_outcome_pattern_run_v1
        ORDER BY source_max_closed_at DESC NULLS LAST,created_at DESC LIMIT 1""")
    source_run = cursor.fetchone()
    if not source_run:
        return None
    purge_before = max(row["label_end_ts"] for row in completed)
    embargo_seconds = max(60, int(max(
        (row["label_end_ts"] - row["label_start_ts"]).total_seconds()
        for row in completed)))
    confirmation_after = purge_before + timedelta(seconds=embargo_seconds)
    hypothesis_key = f"ENTRY_EXIT_V5:{symbol}:{strategy}:{side}:{variant.code}"
    cursor.execute("""INSERT INTO analytics.trade_outcome_hypothesis_v1(
        hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,
        side_code,session_code,holding_code,trades,context_complete_trades,
        profit_factor,expectancy,priority_score,lifecycle_state,recommendation_code,
        evidence,regime_code,symbol)
      VALUES(gen_random_uuid(),%s,%s,'FILTER_OOS_CANDIDATE',%s,%s,'*','*',%s,%s,
        NULL,0,1000,'READY_FOR_OOS','FREEZE_ENTRY_EXIT_FOR_FUTURE_OOS',%s::jsonb,'*',%s)
      ON CONFLICT(hypothesis_key) DO UPDATE SET updated_at=analytics.trade_outcome_hypothesis_v1.updated_at
      RETURNING hypothesis_id""",
      (hypothesis_key,source_run["run_id"],strategy,side,len(completed),len(completed),
       json.dumps({"candidate_code":variant.code,"immutable_after_freeze":True}),symbol))
    hypothesis_id = cursor.fetchone()["hypothesis_id"]
    admission_id = str(uuid.uuid4())
    request = {
        "source":"ENTRY_EXIT_AUTOMATIC_CHAIN_V1",
        "observation_source":"ENTRY_EXIT_SHADOW_V2",
        "family_policy":"EXACT_CANDIDATE_V1",
        "paper_strategy_code":strategy,"strategy_code":strategy,
        "timeframe":timeframe,"side_code":side,"symbol":symbol,
        "session_code":"*","holding_code":"*","regime_code":"*",
        "promotion_allowed":False,
        "frozen_profile":{"candidate_code":variant.code,"entry_mode":variant.entry_mode,
            "stop_atr":variant.stop_atr,"take_atr":variant.take_atr,
            "trail_after_r":variant.trail_after_r,"trail_atr":variant.trail_atr},
        "temporal_isolation":{"policy":"PURGED_EMBARGO_V5_V1","future_data_only":True,
            "purge_before_ts":purge_before.isoformat(),"embargo_seconds":embargo_seconds,
            "confirmation_after_ts":confirmation_after.isoformat()},
    }
    cursor.execute("""INSERT INTO analytics.trade_outcome_oos_admission_v1(
        admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
        microstructure_coverage_ratio,required_microstructure_coverage,status_code,
        reason_code,oos_request,net_expectancy,net_profit_factor,execution_cost,cost_admission_status)
      VALUES(%s,%s,%s,%s,%s,1,0,'QUEUED','ENTRY_EXIT_V5_FROZEN',%s::jsonb,0,NULL,0,
             'ENTRY_EXIT_SHADOW_OOS_QUEUED')""",
      (admission_id,hypothesis_id,symbol,len(completed),len(completed),json.dumps(request)))
    return admission_id


def entry_context_at_signal(cursor, trade: dict, timeframe: str, atr: float,
                            roundtrip_cost_price: float, side: str) -> EntryContext:
    """Build context strictly from bars completed before the signal timestamp."""
    completed_cutoff = trade["entry_ts"] - timeframe_delta(timeframe)
    cursor.execute("""SELECT open::float8,high::float8,low::float8,close::float8,volume::float8
                      FROM market_bars WHERE symbol=%s AND timeframe=%s AND ts <= %s
                      ORDER BY ts DESC LIMIT 80""",
                   (trade["symbol"], timeframe, completed_cutoff))
    history = list(reversed(cursor.fetchall()))
    ranges = [max(float(row["high"]) - float(row["low"]), 0.0) for row in history]
    atr_percentile = (sum(value <= atr for value in ranges) / len(ranges)) if ranges else 0.5
    volumes = [max(float(row["volume"] or 0.0), 0.0) for row in history]
    baseline = median(volumes[:-1]) if len(volumes) > 1 else 0.0
    relative_volume = volumes[-1] / baseline if baseline > 0 and volumes else 1.0
    cursor.execute("""SELECT close::float8 FROM market_bars
                      WHERE symbol=%s AND timeframe='M15'
                        AND ts + interval '15 minutes' <= %s
                      ORDER BY ts DESC LIMIT 8""",
                   (trade["symbol"], trade["entry_ts"]))
    higher_closes = [float(row["close"]) for row in reversed(cursor.fetchall())]
    direction = 1 if side == "LONG" else -1
    higher_timeframe_aligned = (
        len(higher_closes) >= 4
        and direction * (higher_closes[-1] - higher_closes[0]) > 0
    )
    return EntryContext(
        atr_percentile=atr_percentile,
        relative_volume=relative_volume,
        regime=str(trade.get("regime") or "UNKNOWN"),
        cost_to_atr=max(0.0, roundtrip_cost_price) / atr,
        strategy=str(trade["strategy"]),
        higher_timeframe_aligned=higher_timeframe_aligned,
    )


def main() -> int:
    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn, conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("select pg_advisory_xact_lock(hashtext('entry_exit_optimizer_v1'))")
        # Preserve legacy evidence for audit, but fail it closed: the former
        # NEXT_BAR control collides mechanically with CONFIRM_1 candidates.
        cur.execute("""UPDATE analytics.entry_exit_recommendation_v1
          SET recommendation_status='KEEP_SHADOW',
              metrics=jsonb_set(jsonb_set(jsonb_set(
                metrics,'{negative_control,passed}','false'::jsonb,true),
                '{negative_control,reason}','\"INVALID_LEGACY_PLACEBO_NEXT_BAR\"'::jsonb,true),
                '{negative_control,control_code}','\"LEGACY_INVALID_NEXT_BAR_V1\"'::jsonb,true)
          WHERE metrics ? 'negative_control'
            AND coalesce(metrics #>> '{negative_control,control_code}','')=''""")
        # A legacy control must not keep a second candidate alive in the
        # prospective funnel.  Protected V5/Paper stages remain immutable.
        cur.execute("""UPDATE analytics.entry_exit_promotion_workflow_v1 w
          SET workflow_stage='REJECTED',
              statistical_verdict='FAIL',
              evidence=jsonb_set(jsonb_set(w.evidence,
                '{promotion_workflow,selected_for_shadow_funnel}','false'::jsonb,true),
                '{promotion_workflow,selection_reason}',
                '\"LEGACY_PLACEBO_CONTROL_QUARANTINED\"'::jsonb,true),
              last_transition_at=clock_timestamp()
          WHERE w.workflow_stage IN ('SHADOW_ACCUMULATION','EXPENSIVE_GATES_FAILED')
            AND EXISTS (
              SELECT 1 FROM analytics.entry_exit_recommendation_v1 r
              WHERE r.strategy_code=w.strategy_code AND r.symbol_group=w.symbol_group
                AND r.side_code=w.side_code AND r.candidate_code=w.candidate_code
                AND r.metrics #>> '{negative_control,control_code}'='LEGACY_INVALID_NEXT_BAR_V1'
            )""")
        # Diagnostic-only backfill for recommendations frozen before the
        # explicit Gross/Costs/Net contract.  Existing net outcomes are not
        # changed; cost R is reconstructed from the stored pre-entry context.
        cur.execute("""WITH economics AS (
          SELECT p.strategy_code,
                 CASE
                   WHEN p.strategy_code='BR_CONSERVATIVE_BREAKOUT' THEN 'BR'
                   WHEN p.strategy_code='NG_CONSERVATIVE_BREAKOUT_M1' THEN 'NG'
                   WHEN p.strategy_code='CNY_REGIME_FUTURES' THEN 'CNY'
                   WHEN p.strategy_code='USD_REGIME_FUTURES' THEN 'USD'
                   WHEN p.strategy_code='GOLD_TREND_BREAKOUT' THEN 'GOLD'
                   ELSE split_part(p.symbol_code,'@',1)
                 END AS symbol_group,
                 p.side_code,p.candidate_code,
                 avg(p.shadow_net_r + (p.entry_context->>'cost_to_atr')::numeric /
                     nullif(p.stop_atr,0)) AS gross_expectancy_r,
                 avg((p.entry_context->>'cost_to_atr')::numeric /
                     nullif(p.stop_atr,0)) AS roundtrip_cost_r,
                 avg(p.shadow_net_r) AS net_expectancy_r
          FROM analytics.entry_exit_signal_shadow_pair_v2 p
          WHERE p.shadow_net_r IS NOT NULL AND p.entry_context ? 'cost_to_atr'
            AND p.stop_atr>0
          GROUP BY 1,2,3,4
        )
        UPDATE analytics.entry_exit_recommendation_v1 r
          SET metrics=jsonb_set(r.metrics,'{economics_decomposition}',
                jsonb_build_object(
                  'gross_expectancy_r',e.gross_expectancy_r,
                  'roundtrip_cost_r',e.roundtrip_cost_r,
                  'net_expectancy_r',e.net_expectancy_r,
                  'source','DIAGNOSTIC_BACKFILL_FROM_STORED_COST_TO_ATR_V1'),true)
        FROM economics e
        WHERE r.strategy_code=e.strategy_code AND r.symbol_group=e.symbol_group
          AND r.side_code=e.side_code AND r.candidate_code=e.candidate_code
          AND r.metrics #>> '{negative_control,control_code}'='TIME_SHIFTED_ENTRY_V2'
          AND (r.metrics #>> '{economics_decomposition,gross_expectancy_r}' IS NULL
            OR r.metrics #>> '{economics_decomposition,roundtrip_cost_r}' IS NULL)""")
        cur.execute("""
          SELECT s.id,coalesce(nullif(s.signal_id,''),'signal-row:'||s.id::text) signal_id,
                 c.id AS trade_id,s.symbol,s.strategy,
                 upper(s.side) side,coalesce(s.qty,c.qty,1) qty,
                 s.entry_price,s.stop_loss,s.take_profit,
                 coalesce(c.commission,0) commission,
                 coalesce(s.ts,s.created_at) entry_ts,
                 s.status AS source_status,
                 coalesce(s.payload->'context'->>'regime_trend',
                          s.payload->'context'->>'regime',s.regime,'UNKNOWN') regime
          FROM signals s
          LEFT JOIN LATERAL (
            SELECT ct.id,ct.commission,ct.qty FROM closed_trades ct
            WHERE ct.signal_id=s.signal_id AND ct.trade_source='paper'
              AND ct.payload->'pnl_units'->>'version'='PNL_UNITS_V2_RUB'
            ORDER BY coalesce(ct.entry_ts,ct.opened_at,ct.created_at) LIMIT 1
          ) c ON true
          WHERE coalesce(s.payload->'context'->>'cohort',s.payload->>'portfolio_scope','')
                LIKE 'FRESH_V5%%'
            AND s.status IN ('FILLED','RISK_REJECTED')
            AND s.strategy=ANY(%s)
            AND coalesce(s.ts,s.created_at) IS NOT NULL
            AND s.entry_price IS NOT NULL AND s.entry_price>0
          ORDER BY coalesce(s.ts,s.created_at),s.id
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
            completed_horizon_cutoff = datetime.now(
                trade["entry_ts"].tzinfo) - timeframe_delta(SUPPORTED[strategy])
            cur.execute("""SELECT open::float8,high::float8,low::float8,close::float8 FROM market_bars
                           WHERE symbol=%s AND timeframe=%s AND ts > %s AND ts <= %s
                           ORDER BY ts LIMIT %s""",
                        (trade["symbol"], SUPPORTED[strategy], trade["entry_ts"],completed_horizon_cutoff,
                         SHADOW_HORIZON_BARS[strategy]))
            bars = [Bar(float(r["high"]),float(r["low"]),float(r["close"]),float(r["open"]))
                    for r in cur.fetchall()]
            # A partially observed horizon is allowed for accumulation but can
            # never enter selection/promotion statistics.
            horizon_complete = len(bars) == SHADOW_HORIZON_BARS[strategy]
            if not bars:
                continue
            independent_signals.add(independent_key)
            trade["exit_ts"] = trade["entry_ts"] + (
                timeframe_delta(SUPPORTED[strategy]) * SHADOW_HORIZON_BARS[strategy])
            entry_context = entry_context_at_signal(
                cur, trade, SUPPORTED[strategy], float(atr),
                economics["roundtrip_cost_price"], side)
            groups[(strategy,group,side)].append(
                (trade,float(atr),bars,economics,horizon_complete,entry_context))

        family_rows = defaultdict(list)
        for (strategy,group,side), trades in groups.items():
            horizon = timeframe_delta(SUPPORTED[strategy]) * SHADOW_HORIZON_BARS[strategy]
            split = (purged_temporal_split(
                        trades,
                        train_ratio=0.80,
                        start=lambda bundle: bundle[0]["entry_ts"],
                        end=lambda bundle: bundle[0]["entry_ts"] + horizon,
                        embargo=horizon,
                     ) if len(trades) >= 2 else None)
            eligible_ids = ({int(bundle[0]["id"]) for bundle in (*split.train, *split.test)}
                            if split else {int(trades[0][0]["id"])})
            oos_ids = ({int(bundle[0]["id"]) for bundle in split.test} if split else set())
            candidate_results = []
            all_variants = default_variants(strategy) + expert_shadow_variants(strategy)
            # Evaluate one frozen challenger, not the whole grid every cycle.
            # Keep an in-flight candidate stable; after an explicit expensive
            # failure rotate deterministically to another pre-registered arm.
            cur.execute("""SELECT candidate_code FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                  AND workflow_stage IN ('SHADOW_ACCUMULATION','V5_OOS_COLLECTING','V5_OOS_PASS',
                    'PAPER_MINIMAL_ACTIVE','PAPER_MONITOR','PAPER_CONTINUE')
                ORDER BY first_entered_at LIMIT 1""", (strategy,group,side))
            frozen_pool_row = cur.fetchone()
            by_variant_code = {variant.code: variant for variant in all_variants}
            frozen_code = str(frozen_pool_row["candidate_code"]) if frozen_pool_row else ""
            if frozen_code in by_variant_code:
                variants = (by_variant_code[frozen_code],)
            else:
                cur.execute("""SELECT candidate_code FROM analytics.entry_exit_promotion_workflow_v1
                    WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                      AND workflow_stage='EXPENSIVE_GATES_FAILED'""", (strategy,group,side))
                failed_codes = {str(row["candidate_code"]) for row in cur.fetchall()}
                available = [variant for variant in all_variants if variant.code not in failed_codes]
                if not available:
                    available = list(all_variants)
                digest = hashlib.sha256(f"{strategy}|{group}|{side}".encode()).digest()
                variants = (available[int.from_bytes(digest[:4], "big") % len(available)],)
            for variant in variants:
                rows = []
                for trade,atr,bars,economics,horizon_complete,entry_context in trades:
                    risk = atr * variant.stop_atr
                    direction = 1 if side == "LONG" else -1
                    fallback = default_variants(strategy)[0]
                    signal_stop = float(trade.get("stop_loss") or 0.0)
                    signal_take = float(trade.get("take_profit") or 0.0)
                    baseline_stop_atr = (abs(float(trade["entry_price"]) - signal_stop) / atr
                                         if signal_stop > 0 else fallback.stop_atr)
                    baseline_take_atr = (direction * (signal_take - float(trade["entry_price"])) / atr
                                         if signal_take > 0 else fallback.take_atr)
                    if baseline_stop_atr <= 0 or baseline_take_atr <= 0:
                        baseline_stop_atr, baseline_take_atr = fallback.stop_atr, fallback.take_atr
                    baseline = simulate_variant(
                        signal_price=float(trade["entry_price"]), side=side, atr=atr, bars=bars,
                        variant=Variant("CURRENT_PAPER", "IMMEDIATE", baseline_stop_atr, baseline_take_atr),
                        entry_context=entry_context,
                        roundtrip_cost_price=economics["roundtrip_cost_price"],
                        tick_size=economics["tick_size"],
                        stop_slippage_ticks=float(os.getenv("SHADOW_STOP_SLIPPAGE_TICKS", "1")))
                    baseline_net_move = (direction * (float(baseline.exit_price) - float(trade["entry_price"]))
                                         - economics["roundtrip_cost_price"])
                    actual_r = baseline_net_move / risk
                    outcome = simulate_variant(signal_price=float(trade["entry_price"]), side=side, atr=atr,
                                               bars=bars, variant=variant,
                                               entry_context=entry_context,
                                               roundtrip_cost_price=economics["roundtrip_cost_price"],
                                               tick_size=economics["tick_size"],
                                               stop_slippage_ticks=float(os.getenv(
                                                   "SHADOW_STOP_SLIPPAGE_TICKS", "1")))
                    roundtrip_cost_r = economics["roundtrip_cost_price"] / risk
                    placebo_offsets = placebo_entry_offsets(
                        bars_count=len(bars), source_id=int(trade["id"]),
                        candidate_code=variant.code,
                        candidate_delay_bars=int(outcome.entry_delay_bars or 0),
                        samples=int(os.getenv("SHADOW_PLACEBO_TIME_SHIFTS", "20")))
                    placebo_results = [simulate_variant(
                        signal_price=float(bars[offset - 1].close), side=side, atr=atr,
                        bars=bars[offset:],
                        variant=Variant(
                            "PLACEBO_TIME_SHIFT_V2", "IMMEDIATE", variant.stop_atr,
                            variant.take_atr, variant.trail_after_r, variant.trail_atr),
                        entry_context=entry_context,
                        roundtrip_cost_price=economics["roundtrip_cost_price"],
                        tick_size=economics["tick_size"],
                        stop_slippage_ticks=float(os.getenv("SHADOW_STOP_SLIPPAGE_TICKS", "1")),
                    ) for offset in placebo_offsets]
                    placebo_r = (sum(result.net_r for result in placebo_results) /
                                 len(placebo_results) if placebo_results else None)
                    rows.append({"actual_r":actual_r,
                                 "shadow_r":outcome.net_r if horizon_complete else None,
                                 "gross_shadow_r":(outcome.net_r + roundtrip_cost_r
                                                   if horizon_complete and outcome.net_r is not None else None),
                                 "roundtrip_cost_r":roundtrip_cost_r,
                                 "placebo_r":placebo_r if horizon_complete else None,
                                 "placebo_control_code":"TIME_SHIFTED_ENTRY_V2",
                                 "placebo_control_valid":bool(placebo_results),
                                 "placebo_repetitions":len(placebo_results),
                                 "shadow_observed_r": outcome.net_r,
                                 "horizon_complete": horizon_complete,
                                 "trade_date":trade["entry_ts"].date().isoformat(),
                                 "regime":str(trade.get("regime") or "UNKNOWN"),
                                 "entry_decision":outcome.entry_decision,
                                 "entry_decision_reason":outcome.entry_decision_reason,
                                 "entry_delay_bars":outcome.entry_delay_bars,
                                 "entry_slippage_r":outcome.entry_slippage_r,
                                 "mfe_r":outcome.mfe_r,
                                 "mae_r":outcome.mae_r,
                                 "exit_efficiency":outcome.exit_efficiency,
                                 "source_id":int(trade["id"]),
                                 "label_start_ts":trade["entry_ts"],
                                 "label_end_ts":trade["entry_ts"] + horizon})
                    label_end = trade["entry_ts"] + horizon
                    cur.execute("""INSERT INTO analytics.entry_exit_signal_shadow_pair_v2
                      (source_signal_id,signal_id,incumbent_trade_id,source_status,strategy_code,
                       symbol_code,side_code,candidate_code,entry_mode,stop_atr,take_atr,
                       actual_net_r,shadow_entered,shadow_net_r,placebo_net_r,shadow_exit_reason,
                       entry_decision,entry_decision_reason,entry_context,label_start_ts,label_end_ts)
                      VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,
                             %s::jsonb,%s,%s)
                      ON CONFLICT(source_signal_id,candidate_code) DO UPDATE SET
                       actual_net_r=excluded.actual_net_r,shadow_entered=excluded.shadow_entered,
                       shadow_net_r=excluded.shadow_net_r,placebo_net_r=excluded.placebo_net_r,
                       shadow_exit_reason=excluded.shadow_exit_reason,
                       entry_decision=excluded.entry_decision,
                       entry_decision_reason=excluded.entry_decision_reason,
                       entry_context=excluded.entry_context,
                       source_status=excluded.source_status,label_start_ts=excluded.label_start_ts,
                       label_end_ts=excluded.label_end_ts,
                       generated_at=clock_timestamp()""",
                      (trade["id"],trade["signal_id"],trade.get("trade_id"),trade["source_status"],
                       strategy,trade["symbol"],side,variant.code,variant.entry_mode,
                       variant.stop_atr,variant.take_atr,
                       actual_r,outcome.entered,outcome.net_r if horizon_complete else None,
                       placebo_r if horizon_complete else None,
                       outcome.reason if horizon_complete else "PARTIAL_INDEPENDENT_HORIZON",
                       outcome.entry_decision,outcome.entry_decision_reason,
                       json.dumps({"atr_percentile":entry_context.atr_percentile,
                                   "relative_volume":entry_context.relative_volume,
                                   "regime":entry_context.regime,
                                   "cost_to_atr":entry_context.cost_to_atr,
                                   "roundtrip_cost_r":roundtrip_cost_r,
                                   "gross_shadow_r":(outcome.net_r + roundtrip_cost_r
                                                     if outcome.net_r is not None else None),
                                   "strategy":entry_context.strategy,
                                   "higher_timeframe_aligned":
                                       entry_context.higher_timeframe_aligned}),
                       trade["entry_ts"],label_end))
                    cur.execute("""INSERT INTO analytics.entry_exit_shadow_diagnostic_v1(
                        source_signal_id,candidate_code,entry_delay_bars,entry_slippage_r,
                        mfe_r,mae_r,exit_efficiency)
                      VALUES(%s,%s,%s,%s,%s,%s,%s)
                      ON CONFLICT(source_signal_id,candidate_code) DO UPDATE SET
                        entry_delay_bars=excluded.entry_delay_bars,
                        entry_slippage_r=excluded.entry_slippage_r,
                        mfe_r=excluded.mfe_r,mae_r=excluded.mae_r,
                        exit_efficiency=excluded.exit_efficiency,
                        generated_at=clock_timestamp()""",
                      (trade["id"],variant.code,outcome.entry_delay_bars,
                       outcome.entry_slippage_r,outcome.mfe_r,outcome.mae_r,
                       outcome.exit_efficiency))
                evaluation_rows = [row for row in rows if row["source_id"] in eligible_ids]
                explicit_oos = [row for row in rows if row["source_id"] in oos_ids]
                metrics = evaluate_walk_forward(evaluation_rows, oos_rows=explicit_oos)
                statistical_gate = candidate_statistical_gate(
                    evaluation_rows,
                    samples=int(os.getenv("ENTRY_EXIT_STAT_BOOTSTRAP_SAMPLES", "1000")),
                    seed=731 + len(candidate_results),
                )
                metrics["statistical_gate"] = statistical_gate
                futility_gate = candidate_futility_gate(evaluation_rows)
                metrics["futility_gate"] = futility_gate
                completed_cost_rows = [row for row in evaluation_rows
                                       if row.get("shadow_r") is not None]
                metrics["economics_decomposition"] = {
                    "gross_expectancy_r": (sum(float(row["gross_shadow_r"])
                                               for row in completed_cost_rows) /
                                             len(completed_cost_rows)
                                             if completed_cost_rows else None),
                    "roundtrip_cost_r": (sum(float(row["roundtrip_cost_r"])
                                             for row in completed_cost_rows) /
                                           len(completed_cost_rows)
                                           if completed_cost_rows else None),
                    "net_expectancy_r": (sum(float(row["shadow_r"])
                                             for row in completed_cost_rows) /
                                           len(completed_cost_rows)
                                           if completed_cost_rows else None),
                }
                expensive_checks = dict(metrics.get("checks") or {})
                oos_checks = {
                    key: expensive_checks.pop(key) for key in
                    ("oos_positive", "oos_better") if key in expensive_checks
                }
                expensive_pass = bool(expensive_checks) and all(expensive_checks.values())
                if statistical_gate["verdict"] != "PASS":
                    workflow_stage = "SHADOW_ACCUMULATION"
                elif not expensive_pass:
                    workflow_stage = "EXPENSIVE_GATES_FAILED"
                else:
                    workflow_stage = "V5_OOS_COLLECTING"
                metrics["promotion_workflow"] = {
                    "stage": workflow_stage,
                    "statistical_pass": statistical_gate["verdict"] == "PASS",
                    "expensive_gates_pass": expensive_pass,
                    "v5_oos_pass": False,
                    "preliminary_purged_checks": oos_checks,
                    "paper_risk_fraction": 0.25,
                    "real_trading_allowed": False,
                }
                if metrics.get("status") == "READY_FOR_PAPER_CONFIRMATION":
                    metrics["status"] = "KEEP_SHADOW"
                metrics["purged_split"] = {
                    "enabled": True,
                    "boundary": split.boundary.isoformat() if split else None,
                    "test_start": split.test_start.isoformat() if split else None,
                    "purged": split.purged if split else 0,
                    "embargoed": split.embargoed if split else 0,
                    "embargo_seconds": int(horizon.total_seconds()),
                }
                metrics["entry_decisions"] = dict(Counter(
                    row["entry_decision"] for row in rows))
                metrics["entry_decision_reasons"] = dict(Counter(
                    row["entry_decision_reason"] for row in rows))
                metrics["stop_atr"] = variant.stop_atr
                metrics["take_atr"] = variant.take_atr
                metrics["policy_code"] = variant.policy_code
                metrics["shadow_only"] = variant.shadow_only
                metrics["expert_policy_label"] = {
                    "EXPERT_BR": "Brent: тренд, объём и ретест",
                    "EXPERT_NG": "Газ: строгий тренд, объём и ATR",
                    "EXPERT_FX": "Валюты: трендовый ретест после издержек",
                    "EXPERT_GOLD": "Золото: M15, объём и подтверждение",
                    "EXPERT_EQUITY_MR": "Акции: ретест границы диапазона",
                    "EXPERT_EQUITY_BO": "Акции: подтверждённый трендовый пробой",
                }.get(variant.policy_code)
                candidate_results.append((variant, metrics, evaluation_rows))
                all_ids = [int(item[0]["id"]) for item in trades]
                if all_ids:
                    cur.execute("""UPDATE analytics.entry_exit_signal_shadow_pair_v2 SET is_oos=false
                                   WHERE candidate_code=%s AND source_signal_id=ANY(%s)""",
                                (variant.code, all_ids))
                if oos_ids:
                    ids = list(oos_ids)
                    cur.execute("""UPDATE analytics.entry_exit_signal_shadow_pair_v2 SET is_oos=true
                                   WHERE candidate_code=%s AND source_signal_id=ANY(%s)""", (variant.code,ids))
                cur.execute("""INSERT INTO analytics.entry_exit_recommendation_v1
                  (strategy_code,symbol_group,side_code,candidate_code,recommendation_status,pairs,oos_pairs,
                   entry_mode,stop_atr,take_atr,trail_after_r,trail_atr,metrics)
                  VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
                  ON CONFLICT(strategy_code,symbol_group,side_code,candidate_code) DO UPDATE SET
                   recommendation_status=excluded.recommendation_status,pairs=excluded.pairs,oos_pairs=excluded.oos_pairs,
                   metrics=excluded.metrics,generated_at=clock_timestamp()""",
                  (strategy,group,side,variant.code,metrics["status"],metrics["pairs"],
                   int(metrics.get("oos_pairs") or 0),
                   variant.entry_mode,variant.stop_atr,variant.take_atr,variant.trail_after_r,variant.trail_atr,
                   json.dumps(metrics)))
                print("ENTRY_EXIT_SHADOW",strategy,group,side,variant.code,json.dumps(metrics,sort_keys=True))

            metrics_by_code = {variant.code: metrics for variant, metrics, _ in candidate_results}
            for variant, metrics, evaluation_rows in candidate_results:
                plateau = parameter_plateau_check(variant.code, metrics_by_code)
                metrics["parameter_plateau"] = plateau
                if "checks" in metrics:
                    metrics["checks"]["parameter_plateau"] = plateau["passed"]
            freeze_eligible = []
            for item in candidate_results:
                checks = dict(item[1].get("checks") or {})
                for key in ("oos_positive", "oos_better"):
                    checks.pop(key, None)
                if (item[1].get("statistical_gate", {}).get("verdict") == "PASS"
                        and item[1].get("futility_gate", {}).get("verdict") != "REJECT"
                        and checks and all(checks.values()) and not item[0].shadow_only):
                    freeze_eligible.append(item)
            freeze_eligible.sort(key=lambda item: (
                float(item[1].get("shadow_oos_r") or -999),
                float(item[1].get("shadow_expectancy_r") or -999),
                -float(item[1].get("shadow_drawdown_r") or 999)), reverse=True)
            cur.execute("""SELECT candidate_code FROM analytics.entry_exit_promotion_workflow_v1
                WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                  AND admission_id IS NOT NULL
                  AND workflow_stage IN ('V5_OOS_COLLECTING','V5_OOS_PASS','PAPER_MINIMAL_ACTIVE',
                                         'PAPER_MONITOR','PAPER_CONTINUE')
                ORDER BY first_entered_at LIMIT 1""", (strategy,group,side))
            frozen_existing = cur.fetchone()
            freeze_candidate_code = (str(frozen_existing["candidate_code"])
                                     if frozen_existing else
                                     freeze_eligible[0][0].code if freeze_eligible else None)
            # Keep one active research challenger per strategy/instrument/side.
            # All variants remain in the recommendation table for audit, but
            # only this candidate is allowed to consume the expensive/OOS
            # funnel.  This limits multiplicity and prevents UI candidate spam.
            if freeze_candidate_code:
                shadow_funnel_code = freeze_candidate_code
            else:
                viable_candidates = [item for item in candidate_results
                                     if item[1].get("futility_gate", {}).get("verdict") != "REJECT"]
                observed = max(viable_candidates or candidate_results, key=lambda item: (
                    int(item[1].get("pairs") or 0),
                    float(item[1].get("shadow_expectancy_r") or -999),
                    -float(item[1].get("shadow_drawdown_r") or 999),
                ))
                shadow_funnel_code = observed[0].code if viable_candidates else None
            for variant, metrics, evaluation_rows in candidate_results:
                workflow = metrics.get("promotion_workflow") or {}
                checks = dict(metrics.get("checks") or {})
                preliminary_oos = {key: checks.pop(key) for key in
                                   ("oos_positive", "oos_better") if key in checks}
                expensive_pass = bool(checks) and all(checks.values())
                statistical_pass = metrics.get("statistical_gate", {}).get("verdict") == "PASS"
                admission_id = None
                oos_run_id = None
                actual_oos_status = None
                futility_rejected = metrics.get("futility_gate", {}).get("verdict") == "REJECT"
                selected_for_frozen_oos = variant.code == freeze_candidate_code
                selected_for_shadow_funnel = variant.code == shadow_funnel_code
                if selected_for_frozen_oos:
                    cur.execute("""SELECT admission_id,oos_run_id FROM
                        analytics.entry_exit_promotion_workflow_v1
                        WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                          AND candidate_code=%s""", (strategy,group,side,variant.code))
                    existing_workflow = cur.fetchone()
                    if existing_workflow and existing_workflow["admission_id"]:
                        admission_id = str(existing_workflow["admission_id"])
                        oos_run_id = (str(existing_workflow["oos_run_id"])
                                      if existing_workflow["oos_run_id"] else None)
                net_first_values = tuple(
                    Decimal(str(row["shadow_r"]))
                    for row in evaluation_rows
                    if row.get("shadow_r") is not None
                )

                net_first_metrics = build_verified_net_metrics_v1(
                    net_first_values
                )

                net_first_policy = load_economic_cost_gate_policy_v1(
                    Path(__file__).resolve().parents[3]
                    / "config/research/economic_cost_gate_policy_v1.json"
                )

                net_first_admission = (
                    evaluate_verified_net_admission_v1(
                        metrics=net_first_metrics,
                        policy=net_first_policy,
                    )
                )

                net_first_pass = net_first_admission.passed

                metrics["net_first_admission"] = {
                    "status": str(net_first_admission.status),
                    "passed": net_first_pass,
                    "trades": net_first_metrics.trades,
                    "net_expectancy": str(
                        net_first_metrics.net_expectancy
                    ),
                    "net_profit_factor": str(
                        net_first_metrics.net_profit_factor
                    ),
                    "policy_source":
                        "ECONOMIC_COST_GATE_POLICY_V1",
                }

                if (
                    not admission_id
                    and statistical_pass
                    and expensive_pass
                    and net_first_pass
                    and selected_for_frozen_oos
                ):
                    admission_id = ensure_frozen_entry_exit_oos(
                        cur,strategy=strategy,symbol=str(trades[0][0]["symbol"]),side=side,
                        variant=variant,rows=evaluation_rows,timeframe=SUPPORTED[strategy])
                if admission_id:
                    cur.execute("""SELECT r.run_id,r.status_code
                        FROM analytics.v5_oos_run_v1 r WHERE r.admission_id=%s""",
                        (admission_id,))
                    actual_run = cur.fetchone()
                    if actual_run:
                        oos_run_id = str(actual_run["run_id"])
                        actual_oos_status = str(actual_run["status_code"])
                if admission_id and actual_oos_status == "OOS_PASS":
                    workflow_stage = "V5_OOS_PASS"
                elif admission_id and actual_oos_status == "OOS_FAIL":
                    workflow_stage = "V5_OOS_FAILED"
                elif admission_id:
                    workflow_stage = "V5_OOS_COLLECTING"
                elif futility_rejected:
                    workflow_stage = "REJECTED"
                elif not selected_for_shadow_funnel:
                    workflow_stage = "REJECTED"
                elif not statistical_pass:
                    workflow_stage = "SHADOW_ACCUMULATION"
                elif not expensive_pass:
                    workflow_stage = "EXPENSIVE_GATES_FAILED"
                else:
                    workflow_stage = "V5_OOS_COLLECTING"
                workflow.update({
                    "stage":workflow_stage,"statistical_pass":statistical_pass,
                    "expensive_gates_pass":expensive_pass,
                    "v5_oos_pass":actual_oos_status == "OOS_PASS",
                    "v5_oos_status":actual_oos_status or "NOT_STARTED",
                    "admission_id":admission_id,"oos_run_id":oos_run_id,
                    "selected_for_frozen_oos":selected_for_frozen_oos,
                    "selected_for_shadow_funnel":selected_for_shadow_funnel,
                    "selection_reason":(
                        "BEST_EXPENSIVE_GATE_CANDIDATE" if selected_for_frozen_oos
                        else "FUTILITY_GATE_REJECTED" if futility_rejected
                        else "ACTIVE_SHADOW_CHALLENGER" if selected_for_shadow_funnel
                        else "NOT_SELECTED_FOR_SHADOW_FUNNEL"),
                    "preliminary_purged_checks":preliminary_oos,
                })
                metrics["promotion_workflow"] = workflow
                metrics["status"] = ("READY_FOR_PAPER_CONFIRMATION"
                                     if workflow_stage == "V5_OOS_PASS" else "KEEP_SHADOW")
                cur.execute("""UPDATE analytics.entry_exit_recommendation_v1
                               SET recommendation_status=%s,metrics=%s::jsonb,generated_at=clock_timestamp()
                               WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                                 AND candidate_code=%s""",
                            (metrics["status"],json.dumps(metrics),strategy,group,side,variant.code))
                cur.execute("""INSERT INTO analytics.entry_exit_promotion_workflow_v1(
                    strategy_code,symbol_group,side_code,candidate_code,workflow_stage,
                    statistical_verdict,expensive_gates_pass,v5_oos_pass,paper_risk_fraction,
                    evidence,admission_id,oos_run_id,first_entered_at,last_transition_at)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,
                           clock_timestamp(),clock_timestamp())
                    ON CONFLICT(strategy_code,symbol_group,side_code,candidate_code) DO UPDATE SET
                      workflow_stage=excluded.workflow_stage,
                      statistical_verdict=excluded.statistical_verdict,
                      expensive_gates_pass=excluded.expensive_gates_pass,
                      v5_oos_pass=excluded.v5_oos_pass,
                      paper_risk_fraction=excluded.paper_risk_fraction,
                      evidence=excluded.evidence,
                      admission_id=coalesce(excluded.admission_id,
                        analytics.entry_exit_promotion_workflow_v1.admission_id),
                      oos_run_id=coalesce(excluded.oos_run_id,
                        analytics.entry_exit_promotion_workflow_v1.oos_run_id),
                      first_entered_at=CASE WHEN analytics.entry_exit_promotion_workflow_v1.workflow_stage
                        IS DISTINCT FROM excluded.workflow_stage THEN clock_timestamp()
                        ELSE analytics.entry_exit_promotion_workflow_v1.first_entered_at END,
                      last_transition_at=CASE WHEN analytics.entry_exit_promotion_workflow_v1.workflow_stage
                        IS DISTINCT FROM excluded.workflow_stage THEN clock_timestamp()
                        ELSE analytics.entry_exit_promotion_workflow_v1.last_transition_at END,
                      updated_at=clock_timestamp()""",
                    (strategy,group,side,variant.code,
                     workflow.get("stage", "SHADOW_ACCUMULATION"),
                     metrics.get("statistical_gate", {}).get("verdict", "ACCUMULATE"),
                     bool(workflow.get("expensive_gates_pass")),
                     bool(workflow.get("v5_oos_pass")),
                     float(workflow.get("paper_risk_fraction") or 0.25),json.dumps(metrics),
                     admission_id,oos_run_id))
                family_rows[(research_family(strategy),side,variant.code)].extend(evaluation_rows)

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
                     if paper_runtime_supported(group, item[0].entry_mode)
                     and not item[0].shadow_only
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
                    cur.execute("""SELECT coalesce(
                          nullif(payload->>'net_pnl_r','')::numeric,
                          nullif(payload->'context'->>'net_pnl_r','')::numeric
                        ) AS actual_r
                      FROM public.closed_trades
                      WHERE trade_source='paper' AND strategy=%s
                        AND upper(side)=%s AND entry_ts>=%s
                        AND coalesce(
                          payload->'features'->>'entry_exit_candidate_code',
                          payload->'context'->>'entry_exit_candidate_code','')=%s
                        AND coalesce(
                          nullif(payload->'features'->>'entry_exit_profile_id','')::bigint,
                          nullif(payload->'context'->>'entry_exit_profile_id','')::bigint
                        )=%s
                      ORDER BY exit_ts,id""",
                      (strategy,side,active_activated_at,active_code,active_profile_id))
                    champion_rows = [dict(row) for row in cur.fetchall()
                                     if row["actual_r"] is not None]
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
                                AND candidate_code<>'CURRENT_PAPER_BASELINE'
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
                            if (item[0].code == active_code
                                    or not paper_runtime_supported(group, item[0].entry_mode)):
                                continue
                            fresh_rows = [row for row, trade_bundle in zip(item[2], trades)
                                          if trade_bundle[0]["exit_ts"] >= active_activated_at]
                            metrics = evaluate_walk_forward(fresh_rows)
                            fresh_stat = candidate_statistical_gate(fresh_rows)
                            cur.execute("""SELECT workflow_stage FROM
                                analytics.entry_exit_promotion_workflow_v1
                                WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                                  AND candidate_code=%s""",
                                (strategy,group,side,item[0].code))
                            frozen_gate = cur.fetchone()
                            if (metrics.get("status") == "READY_FOR_PAPER_CONFIRMATION"
                                    and fresh_stat.get("verdict") == "PASS"
                                    and frozen_gate
                                    and frozen_gate["workflow_stage"] == "V5_OOS_PASS"):
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
            # Direct full-size promotion is disabled by default.  Automatic
            # continuation happens through the separately guarded minimal
            # adaptive Paper pilot after a strict frozen V5 OOS PASS.
            auto_promotion_enabled = os.getenv("ENTRY_EXIT_AUTO_PROMOTION_ENABLED", "0") == "1"
            if stage == "READY_FOR_CHAMPION_CONFIRMATION" and not auto_promotion_enabled:
                stage = "KEEP_PAPER_CHALLENGER"
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
            workflow_stage_by_challenger = {
                "READY_FOR_CHAMPION_CONFIRMATION": "PAPER_CONTINUE",
                "CHAMPION_ACTIVE": "PAPER_CONTINUE",
                "ROLLED_BACK": "ROLLED_BACK",
                "REJECTED": "REJECTED",
            }
            promoted_workflow_stage = workflow_stage_by_challenger.get(stage)
            if promoted_workflow_stage and existing_code:
                cur.execute("""UPDATE analytics.entry_exit_promotion_workflow_v1
                    SET workflow_stage=%s,
                        evidence=evidence || %s::jsonb,
                        last_transition_at=CASE WHEN workflow_stage IS DISTINCT FROM %s
                          THEN clock_timestamp() ELSE last_transition_at END,
                        updated_at=clock_timestamp()
                    WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                      AND candidate_code=%s""",
                    (promoted_workflow_stage,json.dumps({
                        "paper_stage": stage,
                        "paper_risk_fraction": 0.25,
                        "rollback_after_degraded_daily_cycles": 2,
                        "hard_drawdown_floor_r": 3.0,
                        "real_trading_allowed": False,
                    }),promoted_workflow_stage,strategy,group,side,existing_code))
            print("ENTRY_EXIT_CHALLENGER",strategy,group,side,existing_code,stage,
                  json.dumps(paper_metrics,sort_keys=True))
        conn.commit()
        for (family, side, candidate_code), rows in family_rows.items():
            completed = [row for row in rows if row.get("shadow_r") is not None]
            family_split = (purged_temporal_split(
                completed, train_ratio=0.80,
                start=lambda row: row["label_start_ts"],
                end=lambda row: row["label_end_ts"],
                embargo=max((row["label_end_ts"] - row["label_start_ts"] for row in completed),
                            default=timeframe_delta("M5")),
            ) if len(completed) >= 2 else None)
            eligible = list((*family_split.train, *family_split.test)) if family_split else completed
            oos = list(family_split.test) if family_split else []
            metrics = evaluate_walk_forward(eligible, oos_rows=oos)
            metrics["diagnostic_only"] = True
            metrics["promotion_allowed"] = False
            metrics["family"] = family
            metrics["purged_split"] = {
                "enabled": True,
                "purged": family_split.purged if family_split else 0,
                "embargoed": family_split.embargoed if family_split else 0,
            }
            cur.execute("""INSERT INTO analytics.entry_exit_family_evidence_v1
                (family_code,side_code,candidate_code,evidence_status,pairs,oos_pairs,metrics)
                VALUES(%s,%s,%s,%s,%s,%s,%s::jsonb)
                ON CONFLICT(family_code,side_code,candidate_code) DO UPDATE SET
                  evidence_status=excluded.evidence_status,pairs=excluded.pairs,
                  oos_pairs=excluded.oos_pairs,metrics=excluded.metrics,
                  generated_at=clock_timestamp()""",
                (family,side,candidate_code,metrics["status"],metrics["pairs"],
                 int(metrics.get("oos_pairs") or 0),json.dumps(metrics)))
            print("ENTRY_EXIT_FAMILY_EVIDENCE",family,side,candidate_code,
                  json.dumps(metrics,sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
