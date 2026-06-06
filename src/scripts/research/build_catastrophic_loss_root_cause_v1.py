#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2


TARGET_SYMBOLS = ("PLZL@MISX", "LKOH@MISX", "OZON@MISX")


def conn():
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is not set")
    return psycopg2.connect(dsn)


def main() -> None:
    print("=== CATASTROPHIC LOSS ROOT CAUSE V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print()

    with conn() as c:
        with c.cursor() as cur:
            cur.execute(
                """
                select
                    id,
                    symbol,
                    coalesce(nullif(strategy,''),'unknown') as strategy,
                    coalesce(nullif(timeframe,''),'unknown') as timeframe,
                    side,
                    qty,
                    entry_price,
                    exit_price,
                    net_pnl,
                    gross_pnl,
                    commission,
                    coalesce(opened_at, entry_ts, created_at) as entry_ts,
                    coalesce(closed_at, exit_ts, created_at) as exit_ts,
                    extract(epoch from (
                        coalesce(closed_at, exit_ts, created_at)
                        -
                        coalesce(opened_at, entry_ts, created_at)
                    )) as hold_seconds,
                    trade_source,
                    source,
                    coalesce(
                        payload->>'exit_reason',
                        payload->'exit_payload'->>'exit_reason',
                        payload->'exit_payload'->>'reason',
                        payload->>'reason',
                        'UNKNOWN'
                    ) as exit_reason,
                    payload
                from closed_trades
                where net_pnl is not null
                  and symbol in %s
                order by net_pnl asc
                limit 100;
                """,
                (TARGET_SYMBOLS,),
            )
            rows = cur.fetchall()

    if not rows:
        print("ROWS=0")
        print("VERDICT=NO_TARGET_LOSSES")
        return

    print(f"ROWS={len(rows)}")
    print()

    source_counts = {}
    strategy_counts = {}
    exit_reason_counts = {}
    short_hold_large_loss = 0
    missing_attribution = 0
    suspicious_price_qty = 0

    print("TOP_CATASTROPHIC_LOSSES")

    for row in rows:
        (
            trade_id,
            symbol,
            strategy,
            timeframe,
            side,
            qty,
            entry_price,
            exit_price,
            net_pnl,
            gross_pnl,
            commission,
            entry_ts,
            exit_ts,
            hold_seconds,
            trade_source,
            source,
            exit_reason,
            payload,
        ) = row

        net = float(net_pnl or 0)
        q = float(qty or 0)
        ep = float(entry_price or 0)
        xp = float(exit_price or 0)
        hold = float(hold_seconds or 0)

        source_counts[str(source)] = source_counts.get(str(source), 0) + 1
        strategy_counts[str(strategy)] = strategy_counts.get(str(strategy), 0) + 1
        exit_reason_counts[str(exit_reason)] = exit_reason_counts.get(str(exit_reason), 0) + 1

        if strategy == "unknown" or timeframe == "unknown" or exit_reason == "UNKNOWN":
            missing_attribution += 1

        if hold < 300 and net < -100:
            short_hold_large_loss += 1

        theoretical_move = None
        if ep and xp and q:
            theoretical_move = (xp - ep) * q

        ratio = None
        if theoretical_move not in (None, 0):
            ratio = net / theoretical_move

        if q <= 0 or ep <= 0 or xp <= 0 or (ratio is not None and abs(ratio) > 100):
            suspicious_price_qty += 1

        print(
            f"LOSS_ROW id={trade_id} symbol={symbol} strategy={strategy} timeframe={timeframe} "
            f"side={side} qty={q:.8f} entry_price={ep:.8f} exit_price={xp:.8f} "
            f"net_pnl={net:.8f} gross_pnl={float(gross_pnl or 0):.8f} "
            f"commission={float(commission or 0):.8f} hold_seconds={hold:.2f} "
            f"trade_source={trade_source} source={source} exit_reason={exit_reason} "
            f"move_pnl={0 if theoretical_move is None else theoretical_move:.8f} "
            f"pnl_to_move_ratio={'None' if ratio is None else f'{ratio:.8f}'} "
            f"entry_ts={entry_ts} exit_ts={exit_ts}"
        )

    print()
    print("ROOT_CAUSE_COUNTERS")
    print(f"MISSING_ATTRIBUTION_ROWS={missing_attribution}")
    print(f"SHORT_HOLD_LARGE_LOSS_ROWS={short_hold_large_loss}")
    print(f"SUSPICIOUS_PRICE_QTY_ROWS={suspicious_price_qty}")

    print()
    print("BY_SOURCE")
    for k, v in sorted(source_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"SOURCE_ROW source={k} rows={v}")

    print()
    print("BY_STRATEGY")
    for k, v in sorted(strategy_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"STRATEGY_ROW strategy={k} rows={v}")

    print()
    print("BY_EXIT_REASON")
    for k, v in sorted(exit_reason_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"EXIT_REASON_ROW reason={k} rows={v}")

    print()
    print("DIAGNOSIS")

    if missing_attribution / len(rows) > 0.8:
        print("DIAGNOSIS_ROW code=MISSING_ATTRIBUTION severity=HIGH reason=strategy_timeframe_or_exit_reason_unknown_dominates")

    if short_hold_large_loss / len(rows) > 0.3:
        print("DIAGNOSIS_ROW code=SHORT_HOLD_CATASTROPHIC_LOSS severity=HIGH reason=large_losses_with_hold_lt_5_min")

    if suspicious_price_qty > 0:
        print("DIAGNOSIS_ROW code=PRICE_QTY_OR_MULTIPLIER_SUSPICIOUS severity=HIGH reason=pnl_not_consistent_with_price_move_or_qty")

    print()
    print("VERDICT=OK")


if __name__ == "__main__":
    main()
