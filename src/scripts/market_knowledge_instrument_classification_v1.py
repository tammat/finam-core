from __future__ import annotations

import psycopg2
import psycopg2.extras

SOURCE_VERSION = "MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1"


def classify(symbol: str) -> tuple[str, str]:
    s = symbol.upper()

    if s.startswith("SBER") or s.startswith("VTBR"):
        return "EQUITY", "BANKS"

    if s.startswith("LKOH") or s.startswith("GAZP") or s.startswith("ROSN") or s.startswith("NVTK"):
        return "EQUITY", "OIL_GAS"

    if s.startswith("GMKN") or s.startswith("PLZL") or s.startswith("CHMF") or s.startswith("MAGN"):
        return "EQUITY", "METALS"

    if s.startswith("BR") or s.startswith("NG"):
        return "FUTURES", "COMMODITY"

    if "USD" in s or "EUR" in s or "CNY" in s:
        return "FX", "UNKNOWN"

    return "EQUITY", "UNKNOWN"


def main() -> None:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("""
                SELECT DISTINCT symbol
                FROM analytics.edge_score_model_v2
                WHERE symbol IS NOT NULL
                ORDER BY symbol
            """)
            symbols = [row["symbol"] for row in cur.fetchall()]

            cur.execute("SELECT exchange_id FROM knowledge.exchange_v1 WHERE exchange_code='MOEX' LIMIT 1")
            exchange_id = cur.fetchone()["exchange_id"]

            inserted = 0

            for symbol in symbols:
                asset_class_code, sector_code = classify(symbol)

                cur.execute(
                    "SELECT asset_class_id FROM knowledge.asset_class_v1 WHERE asset_class_code=%s",
                    (asset_class_code,),
                )
                asset_class_id = cur.fetchone()["asset_class_id"]

                cur.execute(
                    "SELECT sector_id FROM knowledge.sector_v1 WHERE sector_code=%s",
                    (sector_code,),
                )
                sector_id = cur.fetchone()["sector_id"]

                cur.execute(
                    """
                    INSERT INTO knowledge.instrument_v1
                    (
                        symbol,
                        exchange_id,
                        asset_class_id,
                        sector_id,
                        instrument_name,
                        currency,
                        is_active,
                        source_version
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,true,%s)
                    ON CONFLICT(symbol) DO UPDATE SET
                        exchange_id=EXCLUDED.exchange_id,
                        asset_class_id=EXCLUDED.asset_class_id,
                        sector_id=EXCLUDED.sector_id,
                        instrument_name=EXCLUDED.instrument_name,
                        currency=EXCLUDED.currency,
                        is_active=true,
                        updated_at=now(),
                        source_version=EXCLUDED.source_version
                    """,
                    (
                        symbol,
                        exchange_id,
                        asset_class_id,
                        sector_id,
                        symbol,
                        "RUB",
                        SOURCE_VERSION,
                    ),
                )
                inserted += 1

    print("=== MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1 ===")
    print(f"classified_symbols={inserted}")
    print("edge_score_v2_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=MARKETCORE_MARKET_KNOWLEDGE_INSTRUMENT_CLASSIFICATION_V1_READY")


if __name__ == "__main__":
    main()
