#!/usr/bin/env python3

import os
import psycopg2


INSTRUMENT_SIG = "MS-A51761DAAE2F"
FX_SIG = "MS-B3C22849CB56"
ENERGY_SIG = "MS-A51761DAAE2F"


def main() -> int:
    print("=== MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_V1 ===")
    print("mode=audit_read_only")
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
                )
                SELECT
                    ct.id::text,
                    ct.symbol,
                    ct.strategy,
                    ct.timeframe,
                    ct.entry_ts,
                    ct.exit_ts,
                    ct.net_pnl,
                    tss.entry_compact_signature,
                    ctx.fx_signature,
                    ctx.energy_signature
                FROM research.trade_state_snapshots_v1 tss
                JOIN public.closed_trades ct
                  ON ct.id::text = tss.trade_id
                JOIN ctx
                  ON ctx.trade_state_id = tss.trade_state_id
                WHERE tss.link_quality='EXACT_OR_NEAREST_OK'
                  AND tss.entry_compact_signature=%s
                  AND ctx.fx_signature=%s
                  AND ctx.energy_signature=%s
                ORDER BY ct.entry_ts;
            """, (INSTRUMENT_SIG, FX_SIG, ENERGY_SIG))
            rows = cur.fetchall()

    wins = sum(1 for r in rows if float(r[6]) > 0)
    losses = sum(1 for r in rows if float(r[6]) <= 0)
    net = sum(float(r[6]) for r in rows)
    gross_profit = sum(float(r[6]) for r in rows if float(r[6]) > 0)
    gross_loss = abs(sum(float(r[6]) for r in rows if float(r[6]) < 0))
    pf = gross_profit / gross_loss if gross_loss > 0 else None
    expectancy = net / len(rows) if rows else 0.0

    print("")
    print("CANDIDATE_SUMMARY")
    print(f"instrument_signature={INSTRUMENT_SIG}")
    print(f"fx_signature={FX_SIG}")
    print(f"energy_signature={ENERGY_SIG}")
    print(f"trades={len(rows)}")
    print(f"wins={wins}")
    print(f"losses={losses}")
    print(f"net_pnl={net:.6f}")
    print(f"expectancy={expectancy:.6f}")
    print(f"profit_factor={pf if pf is not None else 'None'}")

    print("")
    print("CANDIDATE_TRADES")
    for row in rows:
        trade_id, symbol, strategy, timeframe, entry_ts, exit_ts, net_pnl, _, _, _ = row
        print(
            "TRADE "
            f"id={trade_id} "
            f"symbol={symbol} "
            f"strategy={strategy} "
            f"timeframe={timeframe} "
            f"entry_ts={entry_ts} "
            f"exit_ts={exit_ts} "
            f"net_pnl={float(net_pnl):.6f}"
        )

    print("")
    print("NEXT_STEPS")
    print("next=MARKET_STATE_CONTEXT_ROBUSTNESS_CHECK_V1")

    print("")
    print("VERDICT=MARKET_STATE_CONTEXT_CANDIDATE_AUDIT_READY")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
