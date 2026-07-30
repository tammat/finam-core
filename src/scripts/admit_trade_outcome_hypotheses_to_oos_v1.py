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
MIN_TRADES = int(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_TRADES", "80"))


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(184001) AS locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=TRADE_OUTCOME_OOS_ADMISSION_ALREADY_RUNNING")
                return 0
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
                    FROM analytics.fresh_v5_cost_admission_guard_v1 g
                    WHERE (h.symbol IS NULL OR g.symbol=h.symbol)
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
                    status, reason = "WAITING_FRESH_DATA", "FRESH_SAMPLE_BELOW_80"
                elif cost_status != "ELIGIBLE_OOS":
                    status, reason = "REJECTED_COSTS", str(
                        row["cost_reason_code"] or "V5_COST_ADMISSION_NOT_CONFIRMED"
                    )
                elif row["lifecycle_state"] != "READY_FOR_OOS":
                    status, reason = "WAITING_HYPOTHESIS", "HYPOTHESIS_NOT_READY_FOR_OOS"
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
                    "fresh_cohort": "FRESH_V5_CONFIRM", "minimum_closed_trades": MIN_TRADES,
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
                WHERE analytics.trade_outcome_oos_admission_v1.status_code <> 'CLOSED'""",
                    (str(uuid.uuid4()),str(row["hypothesis_id"]),row["symbol"],v5_trades,
                     row["context_complete_trades"],micro,MIN_MICROSTRUCTURE_COVERAGE,status,reason,request,
                     row["net_expectancy"],row["net_profit_factor"],row["execution_cost"],cost_status))
                counts[status] = counts.get(status, 0) + 1
    print(" ".join(f"{status}={count}" for status, count in sorted(counts.items())))
    print(f"VERDICT={SOURCE}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
