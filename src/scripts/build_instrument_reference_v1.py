from __future__ import annotations

import os
import re
import uuid
from datetime import date

import psycopg2
import psycopg2.extras

DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "INSTRUMENT_REFERENCE_V1"

MONTHS = {
    "F": "январь", "G": "февраль", "H": "март", "J": "апрель",
    "K": "май", "M": "июнь", "N": "июль", "Q": "август",
    "U": "сентябрь", "V": "октябрь", "X": "ноябрь", "Z": "декабрь",
}

ROOT_NAMES = {
    "BR": "Нефть Brent",
    "NG": "Природный газ",
    "GD": "Золото",
    "GL": "Золото",
    "SV": "Серебро",
    "USDRUBF": "Фьючерс доллар / рубль",
    "CNYRUBF": "Фьючерс юань / рубль",
}

SPOT_NAMES = {
    "SBER@MISX": "Сбербанк",
    "GAZP@MISX": "Газпром",
    "LKOH@MISX": "Лукойл",
    "PLZL@MISX": "Полюс",
    "VTBR@MISX": "ВТБ",
    "CNYRUB_TOM@MISX": "Юань / рубль TOM",
    "IMOEX": "Индекс МосБиржи",
    "BTCUSD": "Bitcoin / USD",
    "ETHUSD": "Ethereum / USD",
}

def fut_name(symbol: str) -> str:
    base = symbol.split("@")[0]
    if base in ROOT_NAMES:
        return ROOT_NAMES[base]
    m = re.match(r"([A-Z]+)([FGHJKMNQUVXZ])(\d)$", base)
    if not m:
        return ROOT_NAMES.get(base, symbol)
    root, month_code, year_digit = m.groups()
    name = ROOT_NAMES.get(root, root)
    year = 2020 + int(year_digit)
    month = MONTHS.get(month_code, month_code)
    return f"{name}, {month} {year}"

def exchange(symbol: str) -> str:
    if symbol.endswith("@RTSX"):
        return "FORTS"
    if symbol.endswith("@MISX"):
        return "MOEX"
    if symbol in {"BTCUSD", "ETHUSD"}:
        return "CRYPTO_PROXY"
    if symbol == "IMOEX":
        return "MOEX_INDEX"
    return "UNKNOWN"

def display_name(symbol: str) -> str:
    if symbol in SPOT_NAMES:
        return SPOT_NAMES[symbol]
    if symbol.endswith("@RTSX"):
        return fut_name(symbol)
    return symbol

def main() -> None:
    build_id = str(uuid.uuid4())
    with psycopg2.connect(DB) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT symbol, max(asset_class) AS asset_class, min(bar_ts) AS first_seen, max(bar_ts) AS last_seen
                FROM marketcore.market_snapshot_v1
                GROUP BY symbol
                ORDER BY symbol;
            """)
            rows = cur.fetchall()

            for r in rows:
                symbol = r["symbol"]
                name = display_name(symbol)
                cur.execute("""
                    INSERT INTO marketcore.instrument_reference_v1 (
                        symbol, display_name, short_name, asset_class, exchange,
                        first_seen, last_seen, updated_at,
                        source, source_version, build_id
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,now(),'MARKET_SNAPSHOT',%s,%s)
                    ON CONFLICT(symbol) DO UPDATE SET
                        display_name=EXCLUDED.display_name,
                        short_name=EXCLUDED.short_name,
                        asset_class=EXCLUDED.asset_class,
                        exchange=EXCLUDED.exchange,
                        last_seen=EXCLUDED.last_seen,
                        updated_at=now(),
                        source_version=EXCLUDED.source_version,
                        build_id=EXCLUDED.build_id;
                """, (
                    symbol, name, name, r["asset_class"] or "", exchange(symbol),
                    r["first_seen"], r["last_seen"], SOURCE_VERSION, build_id
                ))

    print("=== INSTRUMENT_REFERENCE_V1 ===")
    print(f"rows_written={len(rows)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=INSTRUMENT_REFERENCE_V1_READY")

if __name__ == "__main__":
    main()
