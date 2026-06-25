#!/usr/bin/env python3

import os
import psycopg2


INSTRUMENT_SIG = "MS-A51761DAAE2F"
FX_SIG = "MS-B3C22849CB56"
ENERGY_SIG = "MS-A51761DAAE2F"


def main() -> int:
    print("=== MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1 ===")
    print("mode=robustness_read_only")
    print("db_update=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("ERROR=SQLITE_FORBIDDEN")
        return 2

    with psycopg2.connect(db) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                WITH ctx AS (
                    SELECT
                        l.trade_state_id,
                        MAX(CASE WHEN l.context_code='FX_USDRUB'
                            THEN l.context_compact_signature END) AS fx_signature,
                        MAX(CASE WHEN l.context_code='ENERGY_BR'
                            THEN l.context_compact_signature END) AS energy_signature
                    FROM research.market_state_index_context_links_v1 l
                    WHERE l.link_quality='EXACT_OR_NEAREST_OK'
                    GROUP BY l.trade_state_id
                ),
                candidate AS (
                    SELECT
                        ct.id::text AS trade_id,
                        ct.symbol,
                        ct.strategy,
                        ct.timeframe,
                        ct.entry_ts,
                        ct.exit_ts,
                        ct.net_pnl,
                        DATE(ct.entry_ts) AS trade_day
                    FROM research.trade_state_snapshots_v1 tss
                    JOIN public.closed_trades ct
                      ON ct.id::text = tss.trade_id
                    JOIN ctx
                      ON ctx.trade_state_id = tss.trade_state_id
                    WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                      AND tss.entry_compact_signature=%s
                      AND ctx.fx_signature=%s
                      AND ctx.energy_signature=%s
                )
                SELECT
                    trade_day,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(net_pnl), 0) AS net_pnl,
                    AVG(net_pnl) AS expectancy,
                    MIN(entry_ts) AS first_trade,
                    MAX(entry_ts) AS last_trade
                FROM candidate
                GROUP BY trade_day
                ORDER BY trade_day;
            """, (INSTRUMENT_SIG, FX_SIG, ENERGY_SIG))
            daily_rows = cur.fetchall()

            cur.execute("""
                WITH ctx AS (
                    SELECT
                        l.trade_state_id,
                        MAX(CASE WHEN l.context_code='FX_USDRUB'
                            THEN l.context_compact_signature END) AS fx_signature,
                        MAX(CASE WHEN l.context_code='ENERGY_BR'
                            THEN l.context_compact_signature END) AS energy_signature
                    FROM research.market_state_index_context_links_v1 l
                    WHERE l.link_quality='EXACT_OR_NEAREST_OK'
                    GROUP BY l.trade_state_id
                )
                SELECT
                    ct.symbol,
                    ct.strategy,
                    ct.timeframe,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN ct.net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN ct.net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(ct.net_pnl), 0) AS net_pnl,
                    AVG(ct.net_pnl) AS expectancy
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.closed_trades ct
                  ON ct.id::text = tss.trade_id
                JOIN ctx
                  ON ctx.trade_state_id = tss.trade_state_id
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                  AND tss.entry_compact_signature=%s
                  AND ctx.fx_signature=%s
                  AND ctx.energy_signature=%s
                GROUP BY ct.symbol, ct.strategy, ct.timeframe
                ORDER BY trades DESC, net_pnl DESC;
            """, (INSTRUMENT_SIG, FX_SIG, ENERGY_SIG))
            breakdown_rows = cur.fetchall()

    total_days = len(daily_rows)
    positive_days = sum(1 for r in daily_rows if float(r[4]) > 0)
    negative_days = sum(1 for r in daily_rows if float(r[4]) <= 0)
    total_net = sum(float(r[4]) for r in daily_rows)
    total_trades = sum(int(r[1]) for r in daily_rows)

    print("")
    print("DAILY_ROBUSTNESS")
    for day, trades, wins, losses, net, expectancy, first_ts, last_ts in daily_rows:
        print(
            "DAY "
            f"date={day} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"first_trade={first_ts} "
            f"last_trade={last_ts}"
        )

    print("")
    print("SYMBOL_STRATEGY_BREAKDOWN")
    for symbol, strategy, timeframe, trades, wins, losses, net, expectancy in breakdown_rows:
        print(
            "BREAKDOWN "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f}"
        )

    verdict = "MARKET_STATE_CONTEXT_ROBUSTNESS_WEAK"
    if total_days >= 5 and positive_days >= 3 and total_trades >= 30 and total_net > 0:
        verdict = "MARKET_STATE_CONTEXT_ROBUSTNESS_CANDIDATE_OK"

    print("")
    print("SUMMARY")
    print(f"days_total={total_days}")
    print(f"positive_days={positive_days}")
    print(f"negative_days={negative_days}")
    print(f"trades_total={total_trades}")
    print(f"net_pnl_total={total_net:.6f}")
    print("micro_live_candidates=0")

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_STATE_CONTEXT_FORWARD_VALIDATION_PLAN_V1")
    print("next=MARKET_STATE_CONTEXT_CANDIDATE_REJECTION_V1")

    print("")
    print(f"VERDICT={verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
