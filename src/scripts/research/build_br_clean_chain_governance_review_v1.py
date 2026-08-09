#!/usr/bin/env python3
"""
BR_CLEAN_CHAIN_GOVERNANCE_REVIEW_V1

Read-only решение по BR_CONSERVATIVE_BREAKOUT
на основании только подтверждённых FULL V3 chains.

Никаких изменений runtime/execution.
"""

from __future__ import annotations

import os
from decimal import Decimal

import psycopg2
import psycopg2.extras


STRATEGY = "BR_CONSERVATIVE_BREAKOUT"
TIMEFRAME = "M5"

SYMBOLS = (
    "BRM6@RTSX",
    "BRN6@RTSX",
    "BRQ6@RTSX",
)


def main() -> int:
    print("=== BR CLEAN CHAIN GOVERNANCE REVIEW V1 ===")
    print("mode=research_read_only")
    print("source=closed_trade_chains_v3")
    print("quality_status=FULL")
    print(f"strategy={STRATEGY}")
    print(f"timeframe={TIMEFRAME}")
    print()

    sql = """
    SELECT
        symbol,
        count(*) AS trades,
        sum(net_pnl)::numeric AS net_pnl,
        avg(net_pnl)::numeric AS expectancy,
        sum(
            CASE WHEN net_pnl > 0
                 THEN net_pnl ELSE 0 END
        )::numeric AS gross_profit,
        abs(
            sum(
                CASE WHEN net_pnl < 0
                     THEN net_pnl ELSE 0 END
            )
        )::numeric AS gross_loss
    FROM closed_trade_chains_v3
    WHERE symbol = ANY(%s)
      AND strategy = %s
      AND timeframe = %s
      AND quality_status = 'FULL'
    GROUP BY symbol
    ORDER BY symbol
    """

    conn = psycopg2.connect(os.environ["DATABASE_URL"])
    conn.set_session(readonly=True, autocommit=False)

    try:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                sql,
                (
                    list(SYMBOLS),
                    STRATEGY,
                    TIMEFRAME,
                ),
            )
            rows = [dict(r) for r in cur.fetchall()]

        total_trades = sum(int(r["trades"]) for r in rows)

        total_net = sum(
            Decimal(str(r["net_pnl"] or 0))
            for r in rows
        )

        gross_profit = sum(
            Decimal(str(r["gross_profit"] or 0))
            for r in rows
        )

        gross_loss = sum(
            Decimal(str(r["gross_loss"] or 0))
            for r in rows
        )

        expectancy = (
            total_net / Decimal(total_trades)
            if total_trades else Decimal("0")
        )

        pf = (
            gross_profit / gross_loss
            if gross_loss > 0 else None
        )

        for symbol in SYMBOLS:
            found = next(
                (r for r in rows if r["symbol"] == symbol),
                None,
            )

            if found is None:
                print(
                    "CONTRACT_ROW "
                    f"symbol={symbol} "
                    "full_chains=0 "
                    "status=NO_FULL_CHAIN_EVIDENCE"
                )
                continue

            print(
                "CONTRACT_ROW "
                f"symbol={symbol} "
                f"full_chains={found['trades']} "
                f"net_pnl={found['net_pnl']} "
                f"expectancy={found['expectancy']}"
            )

        if total_trades == 0:
            decision = "INSUFFICIENT_EVIDENCE"
            reason = "no_full_chains"

        elif total_net < 0 and expectancy < 0 and (
            pf is not None and pf < Decimal("1")
        ):
            decision = "REJECT_CURRENT_BR_STRATEGY"
            reason = "negative_clean_full_chain_edge"

        else:
            decision = "CONTINUE_RESEARCH"
            reason = "clean_chain_edge_not_decisively_negative"

        print()
        print(
            "SUMMARY_ROW "
            f"full_chains={total_trades} "
            f"net_pnl={total_net} "
            f"expectancy={expectancy} "
            f"profit_factor={pf}"
        )

        print(f"research_decision={decision}")
        print(f"reason={reason}")

        # Критический safety invariant:
        # этот review ничего не включает.
        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("runtime_allow=0")
        print("execution_enabled=0")

        print(
            "VERDICT="
            f"BR_CLEAN_CHAIN_GOVERNANCE_REVIEW_V1_{decision}"
        )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
