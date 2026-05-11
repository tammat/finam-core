from __future__ import annotations

import os
import psycopg2


INSTRUMENTS = [
    ("LKOH@MISX", "Лукойл", "Лукойл", "stock", "RUB", "manual"),
    ("PLZL@MISX", "Полюс", "Полюс", "stock", "RUB", "manual"),
    ("SBERP@MISX", "Сбербанк ап", "Сбербанк привилегированные акции", "stock", "RUB", "manual"),
    ("VTBR@MISX", "ВТБ", "Банк ВТБ", "stock", "RUB", "manual"),
    ("OZON@MISX", "Ozon", "Ozon Holdings", "stock", "RUB", "manual"),
    ("T@MISX", "Т-Технологии", "Т-Технологии", "stock", "RUB", "manual"),
    ("SFIN@MISX", "ЭсЭфАй", "SFI", "stock", "RUB", "manual"),
    ("X5@MISX", "X5", "X5 Group", "stock", "RUB", "manual"),
    ("NVTK@MISX", "НОВАТЭК", "НОВАТЭК", "stock", "RUB", "manual"),
    ("EUTR@MISX", "ЕвроТранс", "ЕвроТранс", "stock", "RUB", "manual"),
    ("BRM6@RTSX", "BR-6.26", "Фьючерс Brent BR-6.26", "future", "RUB", "manual"),
    ("NGK6@RTSX", "NG-5.26", "Фьючерс Natural Gas NG-5.26", "future", "RUB", "manual"),
    ("SLVRUB_TOM@MISX", "Серебро", "Серебро TOM", "currency", "RUB", "manual"),
    ("SU29010RMFS4@MISX", "ОФЗ 29010", "ОФЗ 29010", "bond", "RUB", "manual"),
    ("SU26243RMFS4@MISX", "ОФЗ 26243", "ОФЗ 26243", "bond", "RUB", "manual"),
]


def main() -> None:
    database_url = os.getenv("DATABASE_URL", "").strip()
    if not database_url:
        raise RuntimeError("DATABASE_URL is required")

    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS instrument_reference (
                    symbol text PRIMARY KEY,
                    short_name text,
                    display_name text,
                    instrument_type text,
                    currency text,
                    source text,
                    updated_at timestamptz DEFAULT now()
                )
            """)

            for row in INSTRUMENTS:
                cur.execute("""
                    INSERT INTO instrument_reference (
                        symbol, short_name, display_name, instrument_type, currency, source, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (symbol) DO UPDATE SET
                        short_name = EXCLUDED.short_name,
                        display_name = EXCLUDED.display_name,
                        instrument_type = EXCLUDED.instrument_type,
                        currency = EXCLUDED.currency,
                        source = EXCLUDED.source,
                        updated_at = now()
                """, row)

    print(f"INSTRUMENT_REFERENCE_SEED_OK saved={len(INSTRUMENTS)}", flush=True)


if __name__ == "__main__":
    main()
