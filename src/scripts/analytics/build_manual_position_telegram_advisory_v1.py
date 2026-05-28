from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.notifications.telegram_advisory_formatter_v1 import TelegramAdvisoryFormatterV1


SQL = """
SELECT
    symbol,
    qty::double precision AS qty,
    avg_price::double precision AS avg_price,
    current_price::double precision AS current_price,
    market_value::double precision AS market_value,
    pnl::double precision AS pnl,
    pnl_day::double precision AS pnl_day,
    updated_at
FROM real_portfolio_positions
WHERE qty <> 0
ORDER BY abs(market_value) DESC;
"""


def detect_asset_class(symbol: str) -> str:
    if "@RTSX" in symbol:
        return "FUTURES"
    if symbol.startswith("SU"):
        return "BOND"
    return "EQUITY"


def calc_side(qty: float) -> str:
    return "LONG" if qty > 0 else "SHORT"


def calc_stop_price(side: str, current_price: float, asset_class: str) -> float:
    if asset_class == "FUTURES":
        stop_pct = 0.012
    elif asset_class == "BOND":
        stop_pct = 0.015
    else:
        stop_pct = 0.03

    if side == "LONG":
        return round(current_price * (1.0 - stop_pct), 4)

    return round(current_price * (1.0 + stop_pct), 4)


def calc_take_price(side: str, current_price: float, asset_class: str) -> float:
    if asset_class == "FUTURES":
        take_pct = 0.025
    elif asset_class == "BOND":
        take_pct = 0.02
    else:
        take_pct = 0.06

    if side == "LONG":
        return round(current_price * (1.0 + take_pct), 4)

    return round(current_price * (1.0 - take_pct), 4)


def build_action(pnl: float) -> str:
    if pnl < -5000:
        return "REVIEW"
    if pnl > 0:
        return "HOLD_PROFIT"
    return "HOLD"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()
    formatter = TelegramAdvisoryFormatterV1()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    futures_count = 0
    review_count = 0

    print("MANUAL_POSITION_TELEGRAM_ADVISORY_V1", flush=True)

    for row in rows:
        symbol = str(row["symbol"])
        qty = float(row["qty"] or 0.0)
        avg_price = float(row["avg_price"] or 0.0)
        current_price = float(row["current_price"] or 0.0)
        pnl = float(row["pnl"] or 0.0)
        pnl_day = float(row["pnl_day"] or 0.0)

        asset_class = detect_asset_class(symbol)
        side = calc_side(qty)
        action = build_action(pnl)

        if asset_class == "FUTURES":
            futures_count += 1

        if action == "REVIEW":
            review_count += 1

        stop_price = calc_stop_price(side, current_price, asset_class)
        take_price = calc_take_price(side, current_price, asset_class)

        msg = formatter.format_position_advisory(
            symbol=symbol,
            asset_class=asset_class,
            side=side,
            qty=qty,
            entry=avg_price,
            current=current_price,
            pnl=pnl,
            pnl_day=pnl_day,
            stop=stop_price,
            take=take_price,
            action=action,
        )

        print(
            "TELEGRAM_ADVISORY_FORMATTED",
            f"severity={msg.severity}",
            f"category={msg.category}",
            f"symbol={msg.symbol}",
            f"title={msg.title}",
            flush=True,
        )

    print(
        "MANUAL_POSITION_TELEGRAM_ADVISORY_SUMMARY",
        f"rows={len(rows)}",
        f"futures={futures_count}",
        f"review_required={review_count}",
        flush=True,
    )

    print(
        "MANUAL_POSITION_TELEGRAM_ADVISORY_V1_OK",
        f"rows={len(rows)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
