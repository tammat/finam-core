#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2

from finam_core.governance.br_long_governance_v1 import BrLongGovernanceV1


def main() -> None:
    mode = os.getenv("BR_LONG_MODE", "shadow")
    dsn = os.getenv("DATABASE_URL")

    print("=== BR LONG GOVERNANCE REPORT V1 ===")
    print("mode=research_only")
    print("execution=disabled")
    print(f"BR_LONG_MODE={mode}")
    print()

    governance = BrLongGovernanceV1(mode=mode)

    sample = [
        ("BRN6@RTSX", "BUY"),
        ("BRN6@RTSX", "LONG"),
        ("BRN6@RTSX", "SELL"),
        ("NGN6@RTSX", "BUY"),
        ("SBER@MISX", "BUY"),
    ]

    allowed = 0
    blocked = 0
    shadow = 0

    print("SAMPLE_DECISIONS")
    for symbol, side in sample:
        decision = governance.evaluate(symbol=symbol, side=side)

        allowed += int(decision.allowed)
        blocked += int(not decision.allowed)
        shadow += int(decision.shadow_logged)

        print(
            f"DECISION_ROW symbol={decision.symbol} side={decision.side} "
            f"mode={decision.mode} allowed={int(decision.allowed)} "
            f"shadow_logged={int(decision.shadow_logged)} reason={decision.reason}"
        )

    print()
    print(
        f"SAMPLE_SUMMARY allowed={allowed} blocked={blocked} "
        f"shadow_logged={shadow}"
    )

    if dsn:
        with psycopg2.connect(dsn) as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    select
                        count(*) filter (
                            where symbol like 'BR%%'
                              and upper(coalesce(side,'')) in ('BUY','LONG')
                        ) as br_long_trades,
                        count(*) filter (
                            where symbol like 'BR%%'
                        ) as br_total_trades
                    from closed_trades ct
                    where ct.net_pnl is not null
                      and not exists (
                          select 1
                          from research_closed_trades_quarantine q
                          where q.trade_id = ct.id
                      );
                """)
                br_long_trades, br_total_trades = cur.fetchone()

        print()
        print(
            f"CLEAN_HISTORY br_long_trades={int(br_long_trades or 0)} "
            f"br_total_trades={int(br_total_trades or 0)}"
        )

    print()
    if mode == "enabled":
        print("VERDICT=BR_LONG_ENABLED")
    elif mode == "disabled":
        print("VERDICT=BR_LONG_DISABLED")
    else:
        print("VERDICT=BR_LONG_SHADOW")


if __name__ == "__main__":
    main()
