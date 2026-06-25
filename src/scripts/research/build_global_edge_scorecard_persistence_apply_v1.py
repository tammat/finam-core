#!/usr/bin/env python3

import os
import psycopg2
from psycopg2.extras import Json

MIN_TRADES = 30
MIN_PROFIT_FACTOR = 1.10
SOURCE_CHECKPOINT = "checkpoint_global_edge_discovery_v1"
SOURCE_SCRIPT = "build_global_edge_scorecard_persistence_apply_v1.py"


def main() -> int:
    print("=== GLOBAL_EDGE_SCORECARD_PERSISTENCE_APPLY_V1 ===")
    print("mode=persistence_apply")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("real_trading_enabled=0")
    print("orders_sent=0")

    db = os.environ.get("DATABASE_URL", "")
    if not db:
        print("db_update=0")
        print("ERROR=DATABASE_URL_NOT_SET")
        return 2
    if db.startswith("sqlite"):
        print("db_update=0")
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
                ),
                scorecard AS (
                    SELECT
                        ct.symbol,
                        ct.strategy,
                        ct.timeframe,
                        tss.entry_compact_signature AS instrument_signature,
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
                )
                SELECT
                    symbol, strategy, timeframe,
                    instrument_signature, fx_signature, energy_signature,
                    trades, wins, losses, net_pnl, expectancy,
                    gross_profit, gross_loss, first_trade, last_trade
                FROM scorecard
                ORDER BY trades DESC, net_pnl DESC;
            """)
            rows = cur.fetchall()

            prepared = []
            positive_rows = 0
            research_candidates = 0
            micro_live_candidates = 0

            for row in rows:
                (
                    symbol, strategy, timeframe,
                    instrument_sig, fx_sig, energy_sig,
                    trades, wins, losses, net, expectancy,
                    gross_profit, gross_loss, first_trade, last_trade,
                ) = row

                gp = float(gross_profit or 0)
                gl = float(gross_loss or 0)
                pf = gp / gl if gl > 0 else None
                winrate = float(wins or 0) / float(trades or 1)
                net_f = float(net or 0)
                exp_f = float(expectancy or 0)

                status = "REJECTED_NEGATIVE_OR_ZERO_EXPECTANCY"
                reason = "net_pnl_or_expectancy_not_positive"

                if net_f > 0 and exp_f > 0:
                    positive_rows += 1
                    status = "POSITIVE_OBSERVATION"
                    reason = "positive_but_not_validated"

                    if int(trades) < MIN_TRADES:
                        status = "REJECTED_INSUFFICIENT_SAMPLE"
                        reason = "trades_below_30"
                    elif pf is None or pf <= MIN_PROFIT_FACTOR:
                        status = "REJECTED_LOW_PROFIT_FACTOR"
                        reason = "profit_factor_below_threshold"
                    else:
                        research_candidates += 1
                        status = "RESEARCH_CANDIDATE"
                        reason = "passes_basic_edge_filters"

                prepared.append({
                    "symbol": symbol,
                    "strategy": strategy,
                    "timeframe": timeframe,
                    "instrument_signature": instrument_sig,
                    "fx_signature": fx_sig,
                    "energy_signature": energy_sig,
                    "trades": int(trades or 0),
                    "wins": int(wins or 0),
                    "losses": int(losses or 0),
                    "winrate": winrate,
                    "net_pnl": net_f,
                    "expectancy": exp_f,
                    "profit_factor": pf,
                    "first_trade": first_trade,
                    "last_trade": last_trade,
                    "first_trade_iso": first_trade.isoformat() if first_trade else None,
                    "last_trade_iso": last_trade.isoformat() if last_trade else None,
                    "status": status,
                    "reason": reason,
                })

            cur.execute("""
                INSERT INTO research.analytics_global_edge_scorecard_runs_v1 (
                    source_script,
                    source_checkpoint,
                    rows_total,
                    positive_rows,
                    research_candidates,
                    micro_live_candidates,
                    research_version,
                    payload
                )
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
                RETURNING run_id;
            """, (
                SOURCE_SCRIPT,
                SOURCE_CHECKPOINT,
                len(prepared),
                positive_rows,
                research_candidates,
                micro_live_candidates,
                "global_edge_scorecard_v1",
                Json({
                    "min_trades": MIN_TRADES,
                    "min_profit_factor": MIN_PROFIT_FACTOR,
                    "note_ru": "Сохранение глобального edge scorecard без promotion.",
                }),
            ))
            run_id = int(cur.fetchone()[0])

            for item in prepared:
                cur.execute("""
                    INSERT INTO research.analytics_global_edge_scorecard_v1 (
                        run_id,
                        symbol,
                        strategy,
                        timeframe,
                        instrument_signature,
                        fx_signature,
                        energy_signature,
                        trades,
                        wins,
                        losses,
                        winrate,
                        net_pnl,
                        expectancy,
                        profit_factor,
                        first_trade,
                        last_trade,
                        status,
                        reason,
                        payload
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s);
                """, (
                    run_id,
                    item["symbol"],
                    item["strategy"],
                    item["timeframe"],
                    item["instrument_signature"],
                    item["fx_signature"],
                    item["energy_signature"],
                    item["trades"],
                    item["wins"],
                    item["losses"],
                    item["winrate"],
                    item["net_pnl"],
                    item["expectancy"],
                    item["profit_factor"],
                    item["first_trade"],
                    item["last_trade"],
                    item["status"],
                    item["reason"],
                    Json({
                        **item,
                        "first_trade": item.get("first_trade_iso"),
                        "last_trade": item.get("last_trade_iso"),
                    }),
                ))

        conn.commit()

    print(f"run_id={run_id}")
    print(f"rows_inserted={len(prepared)}")
    print(f"positive_rows={positive_rows}")
    print(f"research_candidates={research_candidates}")
    print(f"micro_live_candidates={micro_live_candidates}")
    print("db_update=1")
    print("VERDICT=GLOBAL_EDGE_SCORECARD_PERSISTENCE_APPLY_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
