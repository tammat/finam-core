#!/usr/bin/env python3

import os
import psycopg2


def main() -> int:
    print("=== GLOBAL_CONTEXT_SCORECARD_V1 ===")
    print("mode=read_only")
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
                        trade_state_id,
                        MAX(CASE WHEN context_code='FX_USDRUB'
                            THEN context_compact_signature END) AS fx_signature,
                        MAX(CASE WHEN context_code='ENERGY_BR'
                            THEN context_compact_signature END) AS energy_signature
                    FROM research.market_state_index_context_links_v1
                    WHERE link_quality='EXACT_OR_NEAREST_OK'
                    GROUP BY trade_state_id
                )
                SELECT
                    ct.symbol,
                    ct.strategy,
                    ct.timeframe,
                    tss.entry_compact_signature,
                    ctx.fx_signature,
                    ctx.energy_signature,
                    COUNT(*) AS trades,
                    SUM(CASE WHEN ct.net_pnl > 0 THEN 1 ELSE 0 END) AS wins,
                    SUM(CASE WHEN ct.net_pnl <= 0 THEN 1 ELSE 0 END) AS losses,
                    COALESCE(SUM(ct.net_pnl), 0) AS net_pnl,
                    AVG(ct.net_pnl) AS expectancy,
                    SUM(CASE WHEN ct.net_pnl > 0 THEN ct.net_pnl ELSE 0 END) AS gross_profit,
                    ABS(SUM(CASE WHEN ct.net_pnl < 0 THEN ct.net_pnl ELSE 0 END)) AS gross_loss,
                    MIN(ct.entry_ts) AS first_trade,
                    MAX(ct.entry_ts) AS last_trade
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.closed_trades ct
                  ON ct.id::text = tss.trade_id
                JOIN ctx
                  ON ctx.trade_state_id = tss.trade_state_id
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                  AND tss.entry_compact_signature IS NOT NULL
                  AND ctx.fx_signature IS NOT NULL
                  AND ctx.energy_signature IS NOT NULL
                GROUP BY
                    ct.symbol,
                    ct.strategy,
                    ct.timeframe,
                    tss.entry_compact_signature,
                    ctx.fx_signature,
                    ctx.energy_signature
                ORDER BY trades DESC, net_pnl DESC;
            """)
            rows = cur.fetchall()

    print("")
    print("GLOBAL_CONTEXT_SCORECARD_ROWS")

    positive_rows = 0
    research_candidates = 0

    for row in rows:
        (
            symbol,
            strategy,
            timeframe,
            instrument_sig,
            fx_sig,
            energy_sig,
            trades,
            wins,
            losses,
            net,
            expectancy,
            gross_profit,
            gross_loss,
            first_trade,
            last_trade,
        ) = row

        pf = None
        if gross_loss and float(gross_loss) > 0:
            pf = float(gross_profit) / float(gross_loss)

        winrate = float(wins) / float(trades) if trades else 0.0

        status = "INSUFFICIENT_DATA"
        if float(net) > 0 and float(expectancy or 0) > 0:
            positive_rows += 1
            status = "POSITIVE_OBSERVATION"

        if trades >= 30 and float(net) > 0 and float(expectancy or 0) > 0 and pf and pf > 1.1:
            research_candidates += 1
            status = "RESEARCH_CANDIDATE"

        print(
            "SCORECARD_ROW "
            f"symbol={symbol} "
            f"strategy={strategy or 'UNKNOWN'} "
            f"timeframe={timeframe} "
            f"instrument_signature={instrument_sig} "
            f"fx_signature={fx_sig} "
            f"energy_signature={energy_sig} "
            f"trades={trades} "
            f"wins={wins} "
            f"losses={losses} "
            f"winrate={winrate:.4f} "
            f"net_pnl={float(net):.6f} "
            f"expectancy={float(expectancy or 0):.6f} "
            f"profit_factor={pf if pf is not None else 'None'} "
            f"first_trade={first_trade} "
            f"last_trade={last_trade} "
            f"status={status}"
        )

    print("")
    print(f"rows_total={len(rows)}")
    print(f"positive_rows={positive_rows}")
    print(f"research_candidates={research_candidates}")
    print("micro_live_candidates=0")

    print("")
    print("NEXT_STEPS")
    print("next=GLOBAL_EDGE_DISCOVERY_V1")

    print("")
    print("VERDICT=GLOBAL_CONTEXT_SCORECARD_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
