from __future__ import annotations

import os
import uuid
from datetime import timedelta

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE = "TRADE_OUTCOME_OOS_ADMISSION_V1"
MIN_CONTEXT_COVERAGE = float(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_CONTEXT_COVERAGE", "0.80"))
MIN_MICROSTRUCTURE_COVERAGE = float(os.getenv("MICROSTRUCTURE_MIN_COVERAGE", "0.80"))
MIN_TRADES = int(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_TRADES", "15"))
FAMILY_FREEZE_MIN_TRADES = int(os.getenv("V5_FAMILY_FREEZE_MIN_TRADES", "10"))


def _refresh_fresh_v5_hypotheses(cursor) -> int:
    """Регистрирует текущие Paper-когорты; QUEUED/RUNNING OOS не изменяются."""
    cursor.execute("""SELECT max(exit_ts) source_max_closed_at,count(*)::int total,
        count(*) FILTER(WHERE net_pnl>0)::int profitable,
        count(*) FILTER(WHERE net_pnl<0)::int losses
      FROM analytics.closed_trades_fresh_v5_confirmed""")
    source = cursor.fetchone()
    if not source or not int(source["total"] or 0):
        return 0
    cursor.execute("""SELECT run_id FROM analytics.trade_outcome_pattern_run_v1
        WHERE source_max_closed_at=%s ORDER BY created_at DESC LIMIT 1""",
                   (source["source_max_closed_at"],))
    existing = cursor.fetchone()
    run_id = existing["run_id"] if existing else uuid.uuid4()
    if not existing:
        cursor.execute("""INSERT INTO analytics.trade_outcome_pattern_run_v1(
            run_id,source_max_closed_at,total_trades,profitable_trades,loss_trades)
          VALUES(%s,%s,%s,%s,%s)""",
          (str(run_id),source["source_max_closed_at"],source["total"],
           source["profitable"],source["losses"]))
    cursor.execute("""INSERT INTO analytics.trade_outcome_hypothesis_v1(
        hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,
        side_code,session_code,holding_code,trades,context_complete_trades,
        profit_factor,expectancy,priority_score,lifecycle_state,recommendation_code,
        evidence,regime_code,symbol)
      SELECT gen_random_uuid(),
        concat_ws(':','FRESH_V5',g.portfolio_scope,g.symbol,g.strategy_code,g.side_code,
                  g.session_code,g.regime_code,g.exit_code),
        %s,'FILTER_OOS_CANDIDATE',g.strategy_code,g.side_code,g.session_code,g.exit_code,
        g.trades,g.trades,g.net_profit_factor,g.net_expectancy,
        g.trades + greatest(g.net_expectancy,0),
        CASE WHEN g.trades >= %s THEN 'READY_FOR_OOS' ELSE 'WAITING_FRESH_DATA' END,
        CASE WHEN g.trades >= %s THEN 'FREEZE_FOR_FUTURE_OOS'
             ELSE 'ACCUMULATE_FRESH_SAMPLE' END,
        jsonb_build_object('source','FRESH_V5_COHORT_REGISTRATION',
                           'portfolio_scope',g.portfolio_scope,
                           'admission_status',g.admission_status,
                           'reason_code',g.reason_code),
        g.regime_code,g.symbol
      FROM analytics.fresh_v5_frozen_cost_admission_guard_v2 g
      ON CONFLICT(hypothesis_key) DO UPDATE SET
        trades=excluded.trades,context_complete_trades=excluded.context_complete_trades,
        profit_factor=excluded.profit_factor,expectancy=excluded.expectancy,
        priority_score=excluded.priority_score,lifecycle_state=excluded.lifecycle_state,
        recommendation_code=excluded.recommendation_code,evidence=excluded.evidence,
        updated_at=clock_timestamp()
      WHERE NOT EXISTS (
        SELECT 1 FROM analytics.trade_outcome_oos_admission_v1 a
        WHERE a.hypothesis_id=analytics.trade_outcome_hypothesis_v1.hypothesis_id
          AND a.status_code IN ('QUEUED','RUNNING','OOS_PASS','OOS_FAIL','CLOSED')
      )""", (str(run_id), MIN_TRADES, MIN_TRADES))
    return max(0, int(cursor.rowcount or 0))


def _freeze_best_family_candidate(cursor) -> int:
    """Freeze one broad, risk-normalized family for genuinely future-only OOS.

    Exact session/regime/exit cells remain diagnostic.  Selecting one
    instrument/side family avoids starving every OOS run with 1-3 observations.
    The candidate is selected once; an existing admission is immutable.
    """
    cursor.execute("""
        SELECT EXISTS (
          SELECT 1
          FROM analytics.entry_exit_runtime_profile_v1
          WHERE execution_mode='paper' AND status='ACTIVE'
        ) AS has_active_profile
    """)
    profile_state = cursor.fetchone()
    if not profile_state or not profile_state["has_active_profile"]:
        return 0

    cursor.execute("""
        SELECT h.scope_code,h.symbol_code,h.strategy_code,h.side_code,
               h.closed_trades,h.expectancy,h.profit_factor,h.expectancy_r,
               r.candidate_code,r.entry_mode,r.stop_atr,r.take_atr,
               r.trail_after_r,r.trail_atr,r.pairs,
               max(c.exit_ts) AS purge_before_ts,
               greatest(60,ceil(max(extract(epoch FROM (c.exit_ts-c.entry_ts)))))::int
                 AS embargo_seconds,
               max(c.portfolio_scope) AS portfolio_scope
        FROM analytics.hierarchical_evidence_v1 h
        JOIN analytics.entry_exit_recommendation_v1 r
          ON r.strategy_code=h.strategy_code
         AND r.side_code=h.side_code
         AND r.symbol_group=regexp_replace(h.symbol_code,'@.*$','')
        JOIN analytics.entry_exit_runtime_profile_v1 p
          ON p.strategy_code=r.strategy_code
         AND p.symbol_group=r.symbol_group
         AND p.side_code=r.side_code
         AND p.candidate_code=r.candidate_code
         AND p.execution_mode='paper'
         AND p.status='ACTIVE'
        JOIN analytics.closed_trades_fresh_v5_confirmed c
          ON c.symbol=h.symbol_code
         AND coalesce(nullif(c.strategy,''),'UNASSIGNED')=h.strategy_code
         AND upper(coalesce(nullif(c.side,''),'UNKNOWN'))=h.side_code
        WHERE h.cohort_code='FRESH_V5_CONFIRM'
          AND h.level_code='INSTRUMENT_SIDE'
          AND h.closed_trades >= %s
          AND h.expectancy > 0
          AND h.profit_factor_observable
          AND h.profit_factor >= 1.15
          AND h.r_observable
          AND h.expectancy_r > 0
          AND r.pairs >= %s
          AND coalesce((r.metrics->'negative_control'->>'passed')::boolean,false)
          AND coalesce((r.metrics->'negative_control'->>'candidate_expectancy_r')::numeric,0)>0
          AND coalesce((r.metrics->'negative_control'->>'delta_lower_bound_r')::numeric,0)>0
          AND NOT EXISTS (
            SELECT 1
            FROM analytics.trade_outcome_oos_admission_v1 a
            WHERE a.oos_request->>'family_policy'='INSTRUMENT_SIDE_V1'
              AND a.status_code IN ('QUEUED','RUNNING','OOS_PASS','OOS_FAIL')
          )
        GROUP BY h.scope_code,h.symbol_code,h.strategy_code,h.side_code,
                 h.closed_trades,h.expectancy,h.profit_factor,h.expectancy_r,
                 r.candidate_code,r.entry_mode,r.stop_atr,r.take_atr,
                 r.trail_after_r,r.trail_atr,r.pairs,r.metrics
        ORDER BY r.pairs DESC,
                 (r.metrics->'negative_control'->>'delta_lower_bound_r')::numeric DESC,
                 h.closed_trades DESC
        LIMIT 1
    """, (FAMILY_FREEZE_MIN_TRADES,FAMILY_FREEZE_MIN_TRADES))
    candidate = cursor.fetchone()
    if not candidate:
        return 0

    confirmation_after = (
        candidate["purge_before_ts"]
        + timedelta(seconds=int(candidate["embargo_seconds"]))
    )
    hypothesis_key = (
        f"FRESH_V5_FAMILY:{candidate['portfolio_scope']}:{candidate['symbol_code']}:"
        f"{candidate['strategy_code']}:{candidate['side_code']}"
    )
    cursor.execute("""
        SELECT run_id
        FROM analytics.trade_outcome_pattern_run_v1
        ORDER BY source_max_closed_at DESC NULLS LAST,created_at DESC
        LIMIT 1
    """)
    source_run = cursor.fetchone()
    if not source_run:
        return 0
    cursor.execute("""
        INSERT INTO analytics.trade_outcome_hypothesis_v1(
          hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,
          side_code,session_code,holding_code,trades,context_complete_trades,
          profit_factor,expectancy,priority_score,lifecycle_state,recommendation_code,
          evidence,regime_code,symbol)
        VALUES(gen_random_uuid(),%s,%s,'FILTER_OOS_CANDIDATE',%s,%s,'*','*',%s,%s,
               %s,%s,1000,'READY_FOR_OOS','FREEZE_FAMILY_FOR_FUTURE_OOS',
               %s::jsonb,'*',%s)
        ON CONFLICT(hypothesis_key) DO NOTHING
        RETURNING hypothesis_id
    """, (
        hypothesis_key, source_run["run_id"], candidate["strategy_code"],
        candidate["side_code"], candidate["closed_trades"], candidate["closed_trades"],
        candidate["profit_factor"], candidate["expectancy"],
        psycopg2.extras.Json({
            "family_policy": "INSTRUMENT_SIDE_V1",
            "selection_metric": "MATCHED_PAPER_SHADOW_BEATS_PLACEBO",
            "training_expectancy_r": float(candidate["expectancy_r"]),
            "candidate_code": candidate["candidate_code"],
            "entry_mode": candidate["entry_mode"],
            "stop_atr": float(candidate["stop_atr"]),
            "take_atr": float(candidate["take_atr"]),
            "immutable_after_freeze": True,
        }),
        candidate["symbol_code"],
    ))
    inserted = cursor.fetchone()
    if not inserted:
        return 0
    request = psycopg2.extras.Json({
        "source": SOURCE,
        "family_policy": "INSTRUMENT_SIDE_V1",
        "paper_strategy_code": candidate["strategy_code"],
        "strategy_code": candidate["strategy_code"],
        "timeframe": "M5",
        "side_code": candidate["side_code"],
        "symbol": candidate["symbol_code"],
        "session_code": "*",
        "holding_code": "*",
        "regime_code": "*",
        "fresh_cohort": "FRESH_V5_CONFIRMED",
        "minimum_closed_trades": FAMILY_FREEZE_MIN_TRADES,
        "v5_closed_trades": candidate["closed_trades"],
        "net_expectancy": float(candidate["expectancy"]),
        "net_profit_factor": float(candidate["profit_factor"]),
        "promotion_allowed": False,
        "frozen_profile": {
            "candidate_code": candidate["candidate_code"],
            "entry_mode": candidate["entry_mode"],
            "stop_atr": float(candidate["stop_atr"]),
            "take_atr": float(candidate["take_atr"]),
            "trail_after_r": (
                None if candidate["trail_after_r"] is None
                else float(candidate["trail_after_r"])
            ),
            "trail_atr": (
                None if candidate["trail_atr"] is None
                else float(candidate["trail_atr"])
            ),
        },
        "temporal_isolation": {
            "policy": "PURGED_EMBARGO_V5_V1",
            "future_data_only": True,
            "purge_before_ts": candidate["purge_before_ts"].isoformat(),
            "embargo_seconds": int(candidate["embargo_seconds"]),
            "confirmation_after_ts": confirmation_after.isoformat(),
        },
    })
    cursor.execute("""
        INSERT INTO analytics.trade_outcome_oos_admission_v1(
          admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
          microstructure_coverage_ratio,required_microstructure_coverage,status_code,
          reason_code,oos_request,net_expectancy,net_profit_factor,execution_cost,
          cost_admission_status)
        VALUES(gen_random_uuid(),%s,%s,%s,%s,0,0,'QUEUED',
               'READY_FOR_FAMILY_FUTURE_OOS',%s,%s,%s,0,'FAMILY_OOS_QUEUED')
    """, (
        inserted["hypothesis_id"], candidate["symbol_code"],
        candidate["closed_trades"], candidate["closed_trades"], request,
        candidate["expectancy"], candidate["profit_factor"],
    ))
    return 1


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(184001) AS locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=TRADE_OUTCOME_OOS_ADMISSION_ALREADY_RUNNING")
                return 0
            refreshed = _refresh_fresh_v5_hypotheses(cursor)
            family_frozen = _freeze_best_family_candidate(cursor)
            cursor.execute("""SELECT h.hypothesis_id,h.strategy_code,coalesce(sm.oos_strategy_code,h.strategy_code) AS oos_strategy_code,
                       coalesce(sm.oos_timeframe,'M5') AS oos_timeframe,h.side_code,h.symbol,h.session_code,
                       h.holding_code,h.regime_code,h.lifecycle_state,h.recommendation_code,
                       h.trades,h.context_complete_trades,
                       coalesce(m.microstructure_coverage_ratio,0) AS microstructure_coverage_ratio,
                       c.trades AS v5_trades,c.net_expectancy,c.net_profit_factor,
                       c.execution_cost,c.admission_status AS cost_admission_status,
                       c.reason_code AS cost_reason_code,
                       c.last_trade_at AS v5_last_trade_at,
                       coalesce(t.max_holding_seconds,60) AS v5_max_holding_seconds,
                       coalesce(q.quarantined,false) AS early_quarantined,
                       q.quarantine_reason_code
                FROM analytics.trade_outcome_hypothesis_v1 h
                LEFT JOIN analytics.paper_oos_strategy_map_v1 sm
                  ON sm.paper_strategy_code=h.strategy_code AND sm.enabled
                LEFT JOIN LATERAL (
                    SELECT microstructure_coverage_ratio
                    FROM analytics.execution_edge_result_v1 e
                    WHERE e.strategy_code=coalesce(sm.oos_strategy_code,h.strategy_code)
                      AND (h.symbol IS NULL OR e.symbol=h.symbol OR e.symbol LIKE h.symbol || '%')
                      AND e.cohort_code IN ('MICROSTRUCTURE_ONLY','MICROSTRUCTURE_CLEAN_V4')
                    ORDER BY e.created_at DESC LIMIT 1
                ) m ON TRUE
                LEFT JOIN LATERAL (
                    SELECT g.*
                    FROM analytics.fresh_v5_frozen_cost_admission_guard_v2 g
                    WHERE (h.symbol IS NULL OR g.symbol=h.symbol OR g.symbol LIKE h.symbol || '%')
                      AND g.strategy_code=h.strategy_code
                      AND upper(g.side_code)=upper(h.side_code)
                      AND (h.session_code IS NULL OR g.session_code=h.session_code)
                      AND (h.regime_code IS NULL OR g.regime_code=h.regime_code)
                      AND (h.holding_code IS NULL OR g.exit_code=h.holding_code)
                    ORDER BY g.trades DESC,g.last_trade_at DESC
                    LIMIT 1
                ) c ON TRUE
                LEFT JOIN LATERAL (
                    SELECT greatest(60,ceil(max(extract(epoch FROM (v.exit_ts-v.entry_ts)))))::integer
                           AS max_holding_seconds
                    FROM analytics.closed_trades_fresh_v5_confirmed v
                    WHERE v.portfolio_scope=c.portfolio_scope
                      AND v.symbol=c.symbol
                      AND coalesce(nullif(v.strategy,''),'UNASSIGNED')=c.strategy_code
                      AND upper(coalesce(nullif(v.side,''),'UNKNOWN'))=c.side_code
                ) t ON TRUE
                LEFT JOIN analytics.fresh_v5_early_loss_quarantine_v1 q
                  ON q.portfolio_scope=c.portfolio_scope
                 AND q.symbol=c.symbol
                 AND q.strategy_code=c.strategy_code
                 AND q.side_code=c.side_code
                 AND q.session_code=c.session_code
                 AND q.regime_code=c.regime_code
                 AND q.exit_code=c.exit_code
                WHERE h.lifecycle_state <> 'CLOSED'
                ORDER BY h.priority_score DESC""")
            rows = cursor.fetchall()
            counts = {}
            for row in rows:
                context_coverage = float(row["context_complete_trades"]) / max(1, int(row["trades"]))
                micro = float(row["microstructure_coverage_ratio"] or 0)
                v5_trades = int(row["v5_trades"] or 0)
                cost_status = str(row["cost_admission_status"] or "WAITING_SAMPLE")
                purge_before = row["v5_last_trade_at"]
                embargo_seconds = max(60, int(row["v5_max_holding_seconds"] or 60))
                confirmation_after = (
                    purge_before + timedelta(seconds=embargo_seconds)
                    if purge_before is not None else None
                )
                if bool(row["early_quarantined"]):
                    status, reason = "REJECTED_COSTS", str(
                        row["quarantine_reason_code"] or "EARLY_NEGATIVE_AFTER_COSTS"
                    )
                elif v5_trades < MIN_TRADES:
                    status, reason = "WAITING_FRESH_DATA", "FRESH_SAMPLE_BELOW_FREEZE_THRESHOLD"
                elif (
                    float(row["net_expectancy"] or 0) <= 0
                    or float(row["net_profit_factor"] or 0) < 1.15
                ):
                    status, reason = "REJECTED_COSTS", str(
                        row["cost_reason_code"] or "V5_PRE_FREEZE_EDGE_NOT_POSITIVE"
                    )
                elif int(row["context_complete_trades"]) < int(row["trades"]) * MIN_CONTEXT_COVERAGE:
                    status, reason = "WAITING_CONTEXT", "FRESH_CONTEXT_BELOW_THRESHOLD"
                elif micro < MIN_MICROSTRUCTURE_COVERAGE:
                    status, reason = "WAITING_MICROSTRUCTURE", "MICROSTRUCTURE_COVERAGE_BELOW_THRESHOLD"
                else:
                    status, reason = "QUEUED", "READY_FOR_ISOLATED_OOS"
                request = psycopg2.extras.Json({
                    "source": SOURCE, "paper_strategy_code": row["strategy_code"],
                    "strategy_code": row["oos_strategy_code"], "timeframe": row["oos_timeframe"], "side_code": row["side_code"],
                    "symbol": row["symbol"], "session_code": row["session_code"],
                    "holding_code": row["holding_code"], "regime_code": row["regime_code"],
                    "recommendation_code": row["recommendation_code"],
                    "fresh_cohort": "FRESH_V5_CONFIRMED", "minimum_closed_trades": MIN_TRADES,
                    "v5_closed_trades": v5_trades,
                    "net_expectancy": float(row["net_expectancy"] or 0),
                    "net_profit_factor": float(row["net_profit_factor"] or 0),
                    "execution_cost": float(row["execution_cost"] or 0),
                    "cost_admission_status": cost_status,
                    "temporal_isolation": {
                        "policy": "PURGED_EMBARGO_V5_V1",
                        "future_data_only": True,
                        "purge_before_ts": purge_before.isoformat() if purge_before else None,
                        "embargo_seconds": embargo_seconds,
                        "confirmation_after_ts": confirmation_after.isoformat() if confirmation_after else None,
                    },
                    "context_coverage_pct": round(context_coverage * 100, 2),
                    "microstructure_coverage_pct": round(micro * 100, 2),
                    "promotion_allowed": False,
                })
                cursor.execute("""INSERT INTO analytics.trade_outcome_oos_admission_v1(
                    admission_id,hypothesis_id,symbol,fresh_closed_trades,context_complete_trades,
                    microstructure_coverage_ratio,required_microstructure_coverage,status_code,reason_code,oos_request,
                    net_expectancy,net_profit_factor,execution_cost,cost_admission_status
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(hypothesis_id) DO UPDATE SET symbol=excluded.symbol,
                    fresh_closed_trades=excluded.fresh_closed_trades,
                    context_complete_trades=excluded.context_complete_trades,
                    microstructure_coverage_ratio=excluded.microstructure_coverage_ratio,
                    required_microstructure_coverage=excluded.required_microstructure_coverage,
                    status_code=excluded.status_code,reason_code=excluded.reason_code,
                    net_expectancy=excluded.net_expectancy,
                    net_profit_factor=excluded.net_profit_factor,
                    execution_cost=excluded.execution_cost,
                    cost_admission_status=excluded.cost_admission_status,
                    oos_request=excluded.oos_request,updated_at=clock_timestamp()
                WHERE analytics.trade_outcome_oos_admission_v1.status_code NOT IN (
                    'QUEUED','RUNNING','OOS_PASS','OOS_FAIL','CLOSED'
                )""",
                    (str(uuid.uuid4()),str(row["hypothesis_id"]),row["symbol"],v5_trades,
                     row["context_complete_trades"],micro,MIN_MICROSTRUCTURE_COVERAGE,status,reason,request,
                     row["net_expectancy"],row["net_profit_factor"],row["execution_cost"],cost_status))
                counts[status] = counts.get(status, 0) + 1
    print(f"fresh_v5_hypotheses_refreshed={refreshed}")
    print(f"family_oos_candidates_frozen={family_frozen}")
    print(" ".join(f"{status}={count}" for status, count in sorted(counts.items())))
    print(f"VERDICT={SOURCE}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
