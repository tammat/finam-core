from __future__ import annotations

import os

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


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


def calc_heat(market_value: float, total_market_value: float) -> float:
    if total_market_value <= 0:
        return 0.0
    return abs(market_value) / total_market_value


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


def calc_risk_status(pnl: float, heat: float, asset_class: str) -> str:
    if asset_class == "FUTURES" and heat > 0.20:
        return "HIGH_RISK"
    if pnl < -5000:
        return "LOSS_HEAVY"
    if heat > 0.30:
        return "CONCENTRATED"
    return "CONTROLLED"


def calc_action(risk_status: str, pnl: float) -> str:
    if risk_status == "HIGH_RISK":
        return "REDUCE"
    if risk_status == "LOSS_HEAVY":
        return "REVIEW"
    if pnl > 0:
        return "HOLD_PROFIT"
    return "HOLD"


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SQL)
            rows = [dict(r) for r in cur.fetchall()]

    total_market_value = sum(abs(float(r["market_value"] or 0.0)) for r in rows)
    futures_count = 0
    high_risk_count = 0

    print("MANUAL_POSITION_RISK_ADVISORY_V1", flush=True)

    for r in rows:
        symbol = str(r["symbol"])
        qty = float(r["qty"] or 0.0)
        avg_price = float(r["avg_price"] or 0.0)
        current_price = float(r["current_price"] or 0.0)
        market_value = float(r["market_value"] or 0.0)
        pnl = float(r["pnl"] or 0.0)
        pnl_day = float(r["pnl_day"] or 0.0)

        asset_class = detect_asset_class(symbol)
        if asset_class == "FUTURES":
            futures_count += 1

        side = calc_side(qty)
        heat = calc_heat(market_value, total_market_value)
        stop_price = calc_stop_price(side, current_price, asset_class)
        take_price = calc_take_price(side, current_price, asset_class)
        risk_status = calc_risk_status(pnl, heat, asset_class)

        if risk_status != "CONTROLLED":
            high_risk_count += 1

        action = calc_action(risk_status, pnl)

        print(
            "MANUAL_POSITION_RISK_ROW",
            f"symbol={symbol}",
            f"asset_class={asset_class}",
            f"side={side}",
            f"qty={qty}",
            f"entry={avg_price}",
            f"current={current_price}",
            f"market_value={market_value}",
            f"pnl={pnl}",
            f"pnl_day={pnl_day}",
            f"heat={heat:.4f}",
            f"risk_status={risk_status}",
            f"recommended_stop={stop_price}",
            f"recommended_take={take_price}",
            f"action={action}",
            f"updated_at={r['updated_at']}",
            flush=True,
        )

    print(
        "MANUAL_POSITION_RISK_SUMMARY",
        f"rows={len(rows)}",
        f"futures={futures_count}",
        f"high_risk={high_risk_count}",
        f"total_market_value_abs={total_market_value:.2f}",
        flush=True,
    )

    print(f"MANUAL_POSITION_RISK_ADVISORY_V1_OK rows={len(rows)}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
