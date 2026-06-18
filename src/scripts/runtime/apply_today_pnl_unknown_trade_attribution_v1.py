#!/usr/bin/env python3
from __future__ import annotations

import os
from typing import Any

import psycopg2
import psycopg2.extras


# Русский комментарий:
# TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1
# Применяет только безопасное восстановление attribution для сегодняшних UNKNOWN trades.
# Не трогает runtime_active_universe, execution, real trading.
# UPDATE разрешён только при APPLY=1.


UNKNOWN_ROWS_SQL = """
select
    id,
    created_at,
    symbol,
    continuous_symbol,
    strategy,
    timeframe,
    side,
    qty,
    price
from trades
where created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
  )
order by created_at asc, id asc;
"""


UPDATE_SQL = """
update trades
set
    strategy = %s,
    timeframe = %s,
    continuous_symbol = %s
where id = %s
  and created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
  );
"""


VERIFY_SQL = """
select
    count(*) as unknown_rows_after
from trades
where created_at::date = current_date
  and (
        coalesce(strategy, '') = ''
     or strategy in ('UNKNOWN', 'UNKNOWN_STRATEGY')
     or coalesce(timeframe, '') = ''
     or timeframe in ('UNKNOWN', 'UNKNOWN_TIMEFRAME')
  );
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def infer_for_row(row: dict[str, Any]) -> tuple[str, str, str, str]:
    symbol = norm(row.get("symbol"))
    continuous = norm(row.get("continuous_symbol"))

    # Русский комментарий:
    # Для сегодняшнего дефекта план уже подтверждён dry-run: payload дал USDRUB_REGIME/LIVE.
    # Здесь оставляем только консервативный whitelist известных маршрутов.
    if symbol == "USDRUBF@RTSX":
        return "USDRUB_REGIME", "LIVE", continuous or "USDRUB_CONT", "known_usdrub_intraday_fix"

    if symbol == "NGM6@RTSX":
        return "NG_CONSERVATIVE_BREAKOUT_M1", "LIVE", continuous or symbol, "known_ng_m1_fix"

    if symbol == "NGN6@RTSX":
        return "NG_CONSERVATIVE_BREAKOUT_M1", "LIVE", continuous or symbol, "known_ng_m1_fix"

    if symbol == "BRN6@RTSX":
        return "BR_CONSERVATIVE_BREAKOUT", "LIVE", continuous or symbol, "known_br_fix"

    return "UNKNOWN", "UNKNOWN", continuous or symbol, "no_safe_mapping"


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    apply = os.getenv("APPLY", "0") == "1"

    print("=== TODAY PNL UNKNOWN TRADE ATTRIBUTION APPLY V1 ===")
    print(f"mode={'apply' if apply else 'dry_run'}")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print(f"db_update={1 if apply else 0}")
    print()

    plan_rows: list[dict[str, Any]] = []

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(UNKNOWN_ROWS_SQL)
            rows = cur.fetchall()

            for row in rows:
                planned_strategy, planned_timeframe, planned_continuous, source = infer_for_row(row)
                safe = planned_strategy != "UNKNOWN" and planned_timeframe != "UNKNOWN"

                plan = {
                    "id": row.get("id"),
                    "created_at": row.get("created_at"),
                    "symbol": norm(row.get("symbol")),
                    "side": norm(row.get("side")),
                    "qty": row.get("qty"),
                    "price": row.get("price"),
                    "old_strategy": norm(row.get("strategy")) or "NULL",
                    "old_timeframe": norm(row.get("timeframe")) or "NULL",
                    "old_continuous_symbol": norm(row.get("continuous_symbol")) or "NULL",
                    "planned_strategy": planned_strategy,
                    "planned_timeframe": planned_timeframe,
                    "planned_continuous_symbol": planned_continuous,
                    "source": source,
                    "safe": safe,
                }
                plan_rows.append(plan)

                if apply and safe:
                    cur.execute(
                        UPDATE_SQL,
                        (
                            planned_strategy,
                            planned_timeframe,
                            planned_continuous,
                            row.get("id"),
                        ),
                    )

            if apply:
                conn.commit()
            else:
                conn.rollback()

            cur.execute(VERIFY_SQL)
            verify = cur.fetchone() or {}

    print("TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_ROWS")
    for p in plan_rows:
        print(
            "TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_ROW "
            f"id={p['id']} "
            f"created_at={p['created_at']} "
            f"symbol={p['symbol']} "
            f"side={p['side']} "
            f"qty={p['qty']} "
            f"price={p['price']} "
            f"old_strategy={p['old_strategy']} "
            f"old_timeframe={p['old_timeframe']} "
            f"planned_strategy={p['planned_strategy']} "
            f"planned_timeframe={p['planned_timeframe']} "
            f"planned_continuous_symbol={p['planned_continuous_symbol']} "
            f"source={p['source']} "
            f"safe={1 if p['safe'] else 0}"
        )

    safe_count = sum(1 for p in plan_rows if p["safe"])
    unknown_after = int(verify.get("unknown_rows_after") or 0)

    print()
    print("TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_SUMMARY")
    print(f"rows_total={len(plan_rows)}")
    print(f"safe_apply_candidates={safe_count}")
    print(f"applied_rows={safe_count if apply else 0}")
    print(f"unknown_rows_after={unknown_after}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print(f"db_update={1 if apply else 0}")

    if not apply:
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_DRY_RUN_READY")
    elif unknown_after == 0:
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_OK")
    else:
        print("VERDICT=TODAY_PNL_UNKNOWN_ATTRIBUTION_APPLY_PARTIAL_REVIEW_REQUIRED")

    print("TODAY_PNL_UNKNOWN_TRADE_ATTRIBUTION_APPLY_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
