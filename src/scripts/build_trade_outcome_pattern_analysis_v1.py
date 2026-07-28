from __future__ import annotations

import os
import uuid

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE = "TRADE_OUTCOME_PATTERN_ANALYSIS_V1"
MIN_TRADES = int(os.getenv("TRADE_OUTCOME_PATTERN_MIN_TRADES", "20"))


def main() -> int:
    run_id = uuid.uuid4()
    dimensions = {
        "STRATEGY": "coalesce(nullif(strategy,''),'UNKNOWN')",
        "INSTRUMENT": "coalesce(nullif(root_symbol,''), nullif(regexp_replace(symbol,'[A-Z][0-9]@.*$',''),''),'UNKNOWN')",
        "SIDE": "side",
        "REGIME": "coalesce(nullif(entry_regime,''),nullif(regime,''),'UNKNOWN')",
        "TIMEFRAME": "coalesce(nullif(timeframe,''),'UNKNOWN')",
        "SESSION_MSK": """CASE
            WHEN entry_ts IS NULL THEN 'UNKNOWN'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow') < 10 THEN 'PREMARKET'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow') < 14 THEN 'MORNING'
            WHEN extract(hour FROM entry_ts AT TIME ZONE 'Europe/Moscow') < 19 THEN 'DAY'
            ELSE 'EVENING' END""",
        "HOLDING": """CASE
            WHEN coalesce(holding_seconds,hold_seconds,0) < 300 THEN 'UP_TO_5M'
            WHEN coalesce(holding_seconds,hold_seconds,0) < 3600 THEN '5M_TO_1H'
            WHEN coalesce(holding_seconds,hold_seconds,0) < 14400 THEN '1H_TO_4H'
            ELSE 'OVER_4H' END""",
        "STRATEGY_SIDE": "coalesce(nullif(strategy,''),'UNKNOWN') || ' · ' || side",
    }
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("SELECT pg_try_advisory_lock(180901) locked")
            if not cursor.fetchone()["locked"]:
                print("VERDICT=TRADE_OUTCOME_ANALYSIS_ALREADY_RUNNING")
                return 0
            cursor.execute("""SELECT count(*) trades,count(*) FILTER(WHERE net_pnl>0) wins,
                count(*) FILTER(WHERE net_pnl<0) losses,max(coalesce(exit_ts,closed_at,created_at)) latest
                FROM public.closed_trades WHERE trade_source='paper'""")
            summary = cursor.fetchone()
            cursor.execute("""INSERT INTO analytics.trade_outcome_pattern_run_v1(
                run_id,source_max_closed_at,total_trades,profitable_trades,loss_trades)
                VALUES(%s,%s,%s,%s,%s)""", (str(run_id),summary["latest"],summary["trades"],summary["wins"],summary["losses"]))
            written = 0
            for code, expression in dimensions.items():
                cursor.execute(f"""WITH grouped AS (
                    SELECT {expression} value,count(*) trades,
                      count(*) FILTER(WHERE net_pnl>0) winners,count(*) FILTER(WHERE net_pnl<0) losers,
                      coalesce(sum(net_pnl) FILTER(WHERE net_pnl>0),0) gross_profit,
                      abs(coalesce(sum(net_pnl) FILTER(WHERE net_pnl<0),0)) gross_loss,
                      coalesce(avg(net_pnl),0) expectancy
                    FROM public.closed_trades WHERE trade_source='paper' GROUP BY 1)
                    INSERT INTO analytics.trade_outcome_pattern_result_v1(
                      run_id,dimension_code,dimension_value,trades,winners,losers,win_rate,
                      gross_profit,gross_loss,profit_factor,expectancy,outcome_code,recommendation_code)
                    SELECT %s,%s,value,trades,winners,losers,
                      round(winners::numeric/nullif(trades,0),6),gross_profit,gross_loss,
                      CASE WHEN gross_loss>0 THEN gross_profit/gross_loss ELSE NULL END,
                      expectancy,
                      CASE WHEN trades<%s THEN 'INSUFFICIENT_SAMPLE'
                           WHEN expectancy>0 AND gross_profit>gross_loss THEN 'PROFITABLE' ELSE 'LOSS_MAKING' END,
                      CASE WHEN trades<%s THEN 'COLLECT_SAMPLE'
                           WHEN expectancy>0 AND gross_profit>gross_loss THEN 'EXPAND_VALIDATION'
                           ELSE 'RESTRICT_OR_RESEARCH' END
                    FROM grouped""", (str(run_id),code,MIN_TRADES,MIN_TRADES))
                written += cursor.rowcount
    print(f"run_id={run_id}")
    print(f"trades={summary['trades']} winners={summary['wins']} losers={summary['losses']}")
    print(f"patterns={written}")
    print(f"VERDICT={SOURCE}_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
