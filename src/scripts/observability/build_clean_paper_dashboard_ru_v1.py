#!/usr/bin/env python3
from __future__ import annotations

import os
import psycopg2
import psycopg2.extras

SQL = """
select
    symbol,
    strategy,
    timeframe,
    clean_trades,
    trade_days,
    v3_full_chains,
    round(v3_net_pnl, 6) as v3_net_pnl,
    accumulation_status,
    accumulation_reason
from clean_paper_accumulation_tracker_v1
order by v3_full_chains desc, clean_trades desc;
"""

def ru_status(status: str) -> str:
    return {
        "EARLY_ACCUMULATION": "РАННЕЕ НАКОПЛЕНИЕ",
        "NO_V3_CHAINS": "НЕТ V3-ЦЕПОЧЕК",
        "ACCUMULATING": "ИДЁТ НАКОПЛЕНИЕ",
        "RESEARCH_READY": "ГОТОВО К ИССЛЕДОВАНИЮ",
    }.get(status, status)

def ru_reason(reason: str) -> str:
    return {
        "too_few_clean_full_chains": "слишком мало чистых полных V3-цепочек",
        "clean_trades_exist_but_no_v3_chains": "чистые сделки есть, но V3-цепочки не сформированы",
    }.get(reason, reason)

def main() -> int:
    print("=== ЧИСТЫЙ PAPER-КОНТУР V3 ===")
    print("Источник: clean_paper_accumulation_tracker_v1")
    print("Runtime: закрыт")
    print("Real execution: закрыт")
    print("Подтверждённый edge: нет")
    print()

    with psycopg2.connect(os.environ["DATABASE_URL"]) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(SQL)
            rows = cur.fetchall()

    if not rows:
        print("Нет строк чистого paper-накопления.")
        return 0

    for r in rows:
        print(
            f"{r['symbol']} | {r['strategy']} | {r['timeframe']} | "
            f"чистые сделки={r['clean_trades']} | "
            f"дни={r['trade_days']} | "
            f"полные V3={r['v3_full_chains']} | "
            f"PnL={r['v3_net_pnl']} | "
            f"статус={ru_status(r['accumulation_status'])} | "
            f"причина={ru_reason(r['accumulation_reason'])}"
        )

    print()
    print("LEGACY scorecard: не использовать для runtime-решений.")
    print("CLEAN_PAPER_DASHBOARD_RU_V1_OK")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
