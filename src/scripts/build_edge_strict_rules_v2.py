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
        coalesce(nullif(continuous_symbol,''),symbol) AS normalized_symbol,
        upper(strategy) AS strategy,
        upper(side) AS side,
        qty,
        price,
        coalesce(commission,0) AS commission,
        ts,
        coalesce(nullif(payload->>'run_id',''),'live') AS run_key,
        lower(coalesce(payload#>>'{features,is_exit}','false')) IN ('true','1','yes') AS is_exit
    FROM public.trades
    WHERE trade_source='paper'
      AND NOT coalesce(is_invalid,false)
      AND nullif(strategy,'') IS NOT NULL
      AND upper(side) IN ('BUY','SELL')
      AND qty > 0 AND price > 0
      AND ts >= clock_timestamp()-(%s * interval '1 day')
), ordered AS (
    SELECT *,
        lead(side) OVER w AS exit_side,
        lead(qty) OVER w AS exit_qty,
        lead(price) OVER w AS exit_price,
        lead(commission) OVER w AS exit_commission,
        lead(ts) OVER w AS exit_ts,
        lead(is_exit) OVER w AS next_is_exit
    FROM base
    WINDOW w AS (
        PARTITION BY run_key,normalized_symbol,strategy
        ORDER BY ts,id
    )
), pairs AS (
    SELECT
        normalized_symbol,
        strategy,
        side AS entry_side,
        CASE
            WHEN extract(hour FROM ts AT TIME ZONE 'Europe/Moscow') BETWEEN 0 AND 5 THEN 'азиатская_сессия'
            WHEN extract(hour FROM ts AT TIME ZONE 'Europe/Moscow') BETWEEN 6 AND 11 THEN 'утро_мск'
            WHEN extract(hour FROM ts AT TIME ZONE 'Europe/Moscow') BETWEEN 12 AND 15 THEN 'московская_середина'
            WHEN extract(hour FROM ts AT TIME ZONE 'Europe/Moscow') BETWEEN 16 AND 20 THEN 'вечерняя_сессия'
            ELSE 'ночь'
        END AS session_name,
        ts AS entry_ts,
        exit_ts,
        CASE WHEN side='BUY' THEN exit_price-price ELSE price-exit_price END AS pnl_points,
        (
            CASE WHEN side='BUY' THEN exit_price-price ELSE price-exit_price END
        ) * least(qty,exit_qty) - commission - exit_commission AS pnl_after_costs
    FROM ordered
    WHERE NOT is_exit
      AND next_is_exit
      AND exit_side IS NOT NULL
      AND exit_side <> side
      AND exit_price > 0
), aggregated AS (
    SELECT
        normalized_symbol,strategy,entry_side,session_name,
        count(*)::integer AS closed_trades,
        count(*) FILTER(WHERE pnl_after_costs > 0)::integer AS wins,
        count(*) FILTER(WHERE pnl_after_costs <= 0)::integer AS losses,
        sum(pnl_points) AS pnl_points,
        avg(pnl_points) AS expectancy_points,
        sum(pnl_after_costs) AS pnl_after_costs,
        avg(pnl_after_costs) AS expectancy_after_costs,
        min(entry_ts) AS evidence_started_at,
        max(exit_ts) AS evidence_finished_at
    FROM pairs
    GROUP BY normalized_symbol,strategy,entry_side,session_name
)
INSERT INTO analytics.edge_strict_rule_v2(
    normalized_symbol,strategy,entry_side,session_name,closed_trades,wins,losses,
    pnl_points,expectancy_points,pnl_after_costs,expectancy_after_costs,
    rule_action,evidence_started_at,evidence_finished_at,built_at)
SELECT
    normalized_symbol,strategy,entry_side,session_name,closed_trades,wins,losses,
    pnl_points,expectancy_points,pnl_after_costs,expectancy_after_costs,
    CASE
        WHEN closed_trades < %s THEN 'INSUFFICIENT_DATA'
        WHEN expectancy_after_costs > %s THEN 'ALLOW'
        ELSE 'BLOCK'
    END,
    evidence_started_at,evidence_finished_at,clock_timestamp()
FROM aggregated;
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
                    """SELECT lookback_days,min_closed_trades,min_expectancy_after_costs
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
