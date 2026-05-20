from __future__ import annotations

import os
import urllib.request
import json
import psycopg2


def load_moex_last_price(symbol: str) -> float | None:
    secid = symbol.split("@")[0].upper()

    url = (
        "https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"securities/{secid}.json"
        "?iss.meta=off"
        "&marketdata.columns=SECID,LAST,MARKETPRICE,LCURRENTPRICE"
    )

    with urllib.request.urlopen(url, timeout=10) as resp:
        data = json.loads(resp.read().decode("utf-8"))

    md = data.get("marketdata", {})
    cols = md.get("columns", [])
    rows = md.get("data", [])

    if not rows:
        return None

    row = dict(zip(cols, rows[0]))

    for key in ("LAST", "MARKETPRICE", "LCURRENTPRICE"):
        value = row.get(key)
        if value is not None:
            try:
                price = float(value)
                if price > 0:
                    return price
            except Exception:
                pass

    return None


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    symbol = os.getenv("REAL_PRICE_SYNC_SYMBOL", "SBER@MISX").strip().upper()
    price = load_moex_last_price(symbol)

    if price is None:
        print(f"REAL_PORTFOLIO_PRICE_SYNC_NO_PRICE symbol={symbol}")
        return 0

    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                update real_portfolio_positions
                set
                    current_price = %s,
                    market_value = qty * %s,
                    pnl = (qty * %s) - (qty * avg_price),
                    updated_at = now()
                where symbol = %s
                returning symbol, qty, avg_price, current_price, market_value, pnl
            """, (price, price, price, symbol))

            row = cur.fetchone()

            if not row:
                print(f"REAL_PORTFOLIO_PRICE_SYNC_NO_POSITION symbol={symbol}")
                return 0

            s, qty, avg_price, current_price, market_value, pnl = row

            print(
                f"REAL_PORTFOLIO_PRICE_SYNC_UPDATE "
                f"symbol={s} qty={qty} avg_price={avg_price} "
                f"current_price={current_price} market_value={market_value} pnl={pnl}",
                flush=True,
            )

    print("REAL_PORTFOLIO_PRICE_SYNC_OK updated=1")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
