from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE = "TRADE_OUTCOME_HYPOTHESIS_GENERATOR_V1"
MIN_TRADES = int(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_TRADES", "80"))
MIN_SAMPLE_TRADES = int(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_SAMPLE_TRADES", "20"))
MIN_CONTEXT_COVERAGE = float(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_CONTEXT_COVERAGE", "0.80"))
MIN_PROFIT_FACTOR = float(os.getenv("TRADE_OUTCOME_HYPOTHESIS_MIN_PROFIT_FACTOR", "1.15"))


def query_groups(cursor):
    cursor.execute(
        """WITH base AS (
            SELECT
                coalesce(nullif(strategy,''),'UNKNOWN') AS strategy_code,
                coalesce(nullif(side,''),'UNKNOWN') AS side_code,
                coalesce(nullif(root_symbol,''),'UNKNOWN') AS symbol,
                coalesce(nullif(entry_regime,''),nullif(regime,''),'UNKNOWN') AS regime_code,
                coalesce(nullif(payload->'context'->>'entry_session_msk',''),
                    CASE
                      WHEN entry_ts IS NULL THEN 'UNKNOWN'
                      WHEN (entry_ts AT TIME ZONE 'Europe/Moscow')::time < time '10:00' THEN 'PREMARKET'
                      WHEN (entry_ts AT TIME ZONE 'Europe/Moscow')::time < time '14:00' THEN 'MORNING'
                      WHEN (entry_ts AT TIME ZONE 'Europe/Moscow')::time < time '19:00' THEN 'DAY'
                      ELSE 'EVENING'
                    END) AS session_code,
                coalesce(nullif(payload->'context'->>'exit_rule',''),'UNKNOWN') AS exit_rule,
                net_pnl,
                (entry_ts IS NOT NULL
                  AND nullif(root_symbol,'') IS NOT NULL
                  AND coalesce(nullif(entry_regime,''),nullif(regime,'')) IS NOT NULL
                  AND payload->'context'->>'cohort'='FRESH_V2'
                  AND nullif(payload->'context'->>'active_contract','') IS NOT NULL
                  AND nullif(payload->'context'->>'exit_rule','') IS NOT NULL
                  AND payload->'context'->>'exit_rule' <> 'UNSPECIFIED') AS context_complete
            FROM public.closed_trades
            WHERE trade_source='paper'
              AND payload->'context'->>'cohort'='FRESH_V2'
        ), grouped AS (
            SELECT 'FULL_SCOPE' AS scope, strategy_code, side_code, symbol,
                   session_code, exit_rule AS holding_code, regime_code,
                   count(*) AS trades,
                   count(*) FILTER (WHERE context_complete) AS context_complete_trades,
                   coalesce(sum(net_pnl) FILTER (WHERE net_pnl > 0),0) AS gross_profit,
                   abs(coalesce(sum(net_pnl) FILTER (WHERE net_pnl < 0),0)) AS gross_loss,
                   coalesce(avg(net_pnl),0) AS expectancy
            FROM base
            GROUP BY strategy_code,side_code,symbol,session_code,regime_code,exit_rule
        )
        SELECT *, CASE WHEN gross_loss>0 THEN gross_profit/gross_loss ELSE NULL END AS profit_factor
        FROM grouped ORDER BY trades DESC, strategy_code, symbol, side_code LIMIT 500""",
    )
    return cursor.fetchall()


def classify(row, coverage):
    profit_factor = row["profit_factor"]
    profitable = (
        float(row["expectancy"]) > 0
        and profit_factor is not None
        and float(profit_factor) >= MIN_PROFIT_FACTOR
    )
    known_strategy = row["strategy_code"] not in {"UNKNOWN", "unknown", "UNKNOWN_STRATEGY"}
    if int(row["trades"]) < MIN_TRADES:
        return "SAMPLE_EXPANSION", "WAITING_FRESH_DATA", "ACCUMULATE_FRESH_SAMPLE"
    if profitable and coverage >= MIN_CONTEXT_COVERAGE and known_strategy:
        return "FILTER_OOS_CANDIDATE", "READY_FOR_OOS", "QUEUE_ISOLATED_OOS"
    if profitable:
        return "DATA_QUALITY_REMEDIATION", "WAITING_CONTEXT", "COMPLETE_FRESH_CONTEXT"
    return "LOSS_FILTER_REMEDIATION", "RESTRICTED", "RESEARCH_WITHOUT_PROMOTION"


def main() -> int:
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(181001) AS locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=TRADE_OUTCOME_HYPOTHESIS_ALREADY_RUNNING")
                return 0
            cursor.execute("SELECT run_id FROM analytics.trade_outcome_pattern_run_v1 ORDER BY created_at DESC LIMIT 1")
            latest = cursor.fetchone()
            if not latest:
                print("VERDICT=TRADE_OUTCOME_HYPOTHESIS_NO_SOURCE")
                return 0
            run_id = latest["run_id"]
            created = {}
            for row in query_groups(cursor):
                coverage = float(row["context_complete_trades"]) / float(row["trades"])
                hypothesis_type, state, recommendation = classify(row, coverage)
                # The key deliberately excludes lifecycle/type. Reaching 80 trades
                # advances one cumulative cohort instead of creating a new counter.
                key = "|".join(str(value or "-") for value in (
                    "FRESH_V2_FULL_SCOPE", row["strategy_code"], row["side_code"], row["symbol"],
                    row["session_code"], row["holding_code"], row["regime_code"],
                ))
                priority = round(
                    abs(float(row["expectancy"])) * min(2.0, float(row["trades"]) / MIN_TRADES)
                    + (100.0 if float(row["expectancy"]) > 0 else 0.0)
                    + (20.0 if coverage < MIN_CONTEXT_COVERAGE else 0.0), 6)
                evidence = psycopg2.extras.Json({
                    "source": SOURCE, "scope": row["scope"],
                    "context_coverage_pct": round(coverage * 100, 2),
                    "minimum_trades": MIN_TRADES, "minimum_sample_trades": MIN_SAMPLE_TRADES,
                    "minimum_profit_factor": MIN_PROFIT_FACTOR, "promotion_allowed": False,
                })
                cursor.execute("""INSERT INTO analytics.trade_outcome_hypothesis_v1(
                    hypothesis_id,hypothesis_key,source_run_id,hypothesis_type,strategy_code,side_code,symbol,
                    session_code,holding_code,regime_code,trades,context_complete_trades,profit_factor,
                    expectancy,priority_score,lifecycle_state,recommendation_code,evidence
                ) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT(hypothesis_key) DO UPDATE SET
                    source_run_id=excluded.source_run_id,trades=excluded.trades,
                    context_complete_trades=excluded.context_complete_trades,
                    profit_factor=excluded.profit_factor,expectancy=excluded.expectancy,
                    priority_score=excluded.priority_score,lifecycle_state=excluded.lifecycle_state,
                    recommendation_code=excluded.recommendation_code,evidence=excluded.evidence,
                    updated_at=clock_timestamp()""",
                    (str(uuid.uuid4()), key, str(run_id), hypothesis_type, row["strategy_code"], row["side_code"],
                     row["symbol"], row["session_code"], row["holding_code"], row["regime_code"], row["trades"],
                     row["context_complete_trades"], row["profit_factor"], row["expectancy"], priority,
                     state, recommendation, evidence))
                created[hypothesis_type] = created.get(hypothesis_type, 0) + 1
    print("source_run_id=" + str(run_id))
    print(" ".join(f"{code}={count}" for code, count in sorted(created.items())))
    print(f"VERDICT={SOURCE}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
