from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
LOCK_ID = 941903130


BUILD_SQL = """
WITH base AS (
    SELECT
        id,
        CASE
          WHEN symbol ~ '^BR[FGHJKMNQUVXZ][0-9]*@RTSX$' THEN 'BR_CONT'
          WHEN symbol ~ '^NG[FGHJKMNQUVXZ][0-9]*@RTSX$' THEN 'NG_CONT'
          WHEN symbol LIKE 'USDRUB%%@RTSX' THEN 'USDRUB_CONT'
          ELSE coalesce(nullif(root_symbol,''),symbol)
        END AS normalized_symbol,
        upper(strategy) AS strategy,
        CASE upper(side) WHEN 'LONG' THEN 'BUY' WHEN 'SHORT' THEN 'SELL' ELSE upper(side) END AS entry_side,
        CASE WHEN upper(strategy)='BR_CONSERVATIVE_BREAKOUT' AND upper(coalesce(timeframe,'')) IN ('','LIVE','UNKNOWN')
             THEN 'M5' ELSE upper(coalesce(nullif(timeframe,''),'UNKNOWN')) END AS timeframe,
        lower(coalesce(
          nullif(nullif(upper(coalesce(entry_regime,'')),'UNKNOWN'),''),
          nullif(nullif(upper(coalesce(regime,'')),'UNKNOWN'),''),
          'UNKNOWN'
        )) AS regime_code,
        entry_ts,exit_ts,
        coalesce(gross_pnl,net_pnl+coalesce(commission,0)) AS pnl_points,
        net_pnl AS pnl_after_costs
    FROM public.closed_trades
    WHERE trade_source='paper'
      AND nullif(strategy,'') IS NOT NULL
      AND upper(side) IN ('BUY','SELL','LONG','SHORT')
      AND entry_ts IS NOT NULL AND exit_ts IS NOT NULL
      AND net_pnl IS NOT NULL
      AND exit_ts >= clock_timestamp()-(%s * interval '1 day')
), classified AS (
    SELECT *,
        CASE
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 600 AND 629 THEN 'MOEX_OPEN'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 630 AND 659 THEN 'MOEX_FIRST_HOUR'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 660 AND 989 THEN 'EUROPE_OVERLAP'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 990 AND 1079 THEN 'US_OPEN'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 1080 AND 1419 THEN 'EVENING'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow')*60
               + extract(minute FROM entry_ts AT TIME ZONE 'Europe/Moscow') BETWEEN 1420 AND 1429 THEN 'MOEX_CLOSE'
            ELSE 'OUTSIDE_SESSION'
        END AS session_name
    FROM base
), aggregated AS (
    SELECT
        normalized_symbol,strategy,timeframe,entry_side,session_name,regime_code,
        count(*)::integer AS closed_trades,
        count(*) FILTER(WHERE pnl_after_costs > 0)::integer AS wins,
        count(*) FILTER(WHERE pnl_after_costs <= 0)::integer AS losses,
        sum(pnl_points) AS pnl_points,
        avg(pnl_points) AS expectancy_points,
        sum(pnl_after_costs) AS pnl_after_costs,
        avg(pnl_after_costs) AS expectancy_after_costs,
        min(entry_ts) AS evidence_started_at,
        max(exit_ts) AS evidence_finished_at
    FROM classified
    GROUP BY normalized_symbol,strategy,timeframe,entry_side,session_name,regime_code
), coverage AS (
    SELECT DISTINCT ON (normalized_symbol,strategy_code,timeframe,regime_code,session_code)
        normalized_symbol,strategy_code AS strategy,timeframe,regime_code,session_code,
        microstructure_coverage_ratio,cohort_code
    FROM (
      SELECT e.*,
        CASE
          WHEN symbol ~ '^BR[FGHJKMNQUVXZ][0-9]*@RTSX$' THEN 'BR_CONT'
          WHEN symbol ~ '^NG[FGHJKMNQUVXZ][0-9]*@RTSX$' THEN 'NG_CONT'
          ELSE symbol
        END AS normalized_symbol
      FROM analytics.execution_edge_result_v1 e
      WHERE cohort_code='MICROSTRUCTURE_CLEAN_V4'
    ) e
    ORDER BY normalized_symbol,strategy_code,timeframe,regime_code,session_code,created_at DESC
)
INSERT INTO analytics.edge_strict_rule_v2(
    normalized_symbol,strategy,timeframe,entry_side,session_name,regime_code,closed_trades,wins,losses,
    pnl_points,expectancy_points,pnl_after_costs,expectancy_after_costs,
    microstructure_coverage_ratio,evidence_cohort_code,rule_action,
    evidence_started_at,evidence_finished_at,built_at)
SELECT
    a.normalized_symbol,a.strategy,a.timeframe,a.entry_side,a.session_name,a.regime_code,
    a.closed_trades,a.wins,a.losses,
    pnl_points,expectancy_points,pnl_after_costs,expectancy_after_costs,
    coalesce(c.microstructure_coverage_ratio,0),coalesce(c.cohort_code,'UNVERIFIED'),
    CASE
        WHEN closed_trades < %s THEN 'INSUFFICIENT_DATA'
        WHEN coalesce(c.microstructure_coverage_ratio,0) < %s THEN 'INSUFFICIENT_DATA'
        WHEN expectancy_after_costs > %s THEN 'ALLOW'
        ELSE 'BLOCK'
    END,
    evidence_started_at,evidence_finished_at,clock_timestamp()
FROM aggregated a
LEFT JOIN coverage c ON c.normalized_symbol=a.normalized_symbol
 AND c.strategy=a.strategy AND c.timeframe=a.timeframe
 AND c.regime_code=a.regime_code AND c.session_code=a.session_name;
"""


def main() -> int:
    build_run_id = str(uuid.uuid4())
    try:
        with psycopg2.connect(DB) as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute("SELECT pg_try_advisory_xact_lock(%s) locked", (LOCK_ID,))
                if not cursor.fetchone()["locked"]:
                    print("VERDICT=EDGE_STRICT_RULE_BUILD_ALREADY_RUNNING")
                    return 0
                cursor.execute(
                    """SELECT lookback_days,min_closed_trades,min_expectancy_after_costs,
                              min_microstructure_coverage
                       FROM analytics.edge_strict_rule_policy_v2
                       WHERE enabled ORDER BY updated_at DESC LIMIT 1"""
                )
                policy = cursor.fetchone()
                if policy is None:
                    raise RuntimeError("EDGE_STRICT_RULE_POLICY_MISSING")
                cursor.execute(
                    """INSERT INTO analytics.edge_strict_rule_build_run_v2(
                           build_run_id,status_code) VALUES(%s,'RUNNING')""",
                    (build_run_id,),
                )
                cursor.execute("DELETE FROM analytics.edge_strict_rule_v2")
                cursor.execute(
                    BUILD_SQL,
                    (
                        policy["lookback_days"],
                        policy["min_closed_trades"],
                        policy["min_microstructure_coverage"],
                        policy["min_expectancy_after_costs"],
                    ),
                )
                cursor.execute(
                    """SELECT count(*) rules_total,
                              count(*) FILTER(WHERE rule_action='ALLOW') allow_total,
                              count(*) FILTER(WHERE rule_action='BLOCK') block_total,
                              count(*) FILTER(WHERE rule_action='INSUFFICIENT_DATA') insufficient_total
                       FROM analytics.edge_strict_rule_v2"""
                )
                totals = cursor.fetchone()
                cursor.execute(
                    """UPDATE analytics.edge_strict_rule_build_run_v2
                       SET status_code='COMPLETE',rules_total=%s,allow_total=%s,
                           block_total=%s,insufficient_total=%s,finished_at=clock_timestamp()
                       WHERE build_run_id=%s""",
                    (
                        totals["rules_total"],
                        totals["allow_total"],
                        totals["block_total"],
                        totals["insufficient_total"],
                        build_run_id,
                    ),
                )
        print(f"rules_total={totals['rules_total']}")
        print(f"allow_total={totals['allow_total']}")
        print(f"block_total={totals['block_total']}")
        print(f"insufficient_total={totals['insufficient_total']}")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("real_trading_enabled=0")
        print("VERDICT=EDGE_STRICT_RULE_BUILD_V2_OK")
        return 0
    except Exception as exc:
        try:
            with psycopg2.connect(DB) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """INSERT INTO analytics.edge_strict_rule_build_run_v2(
                               build_run_id,status_code,error_text,finished_at)
                           VALUES(%s,'FAILED',%s,clock_timestamp())
                           ON CONFLICT(build_run_id) DO UPDATE SET
                               status_code='FAILED',error_text=excluded.error_text,
                               finished_at=excluded.finished_at""",
                        (build_run_id, f"{type(exc).__name__}:{exc}"[:4000]),
                    )
        except Exception:
            pass
        raise


if __name__ == "__main__":
    raise SystemExit(main())
