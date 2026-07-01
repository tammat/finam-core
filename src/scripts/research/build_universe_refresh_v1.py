from __future__ import annotations

import os
from dataclasses import dataclass

import psycopg2


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")


@dataclass(frozen=True)
class UniverseRow:
    symbol: str
    asset_class: str
    source: str
    status: str


DEFAULT_UNIVERSE = [
    UniverseRow("BR@RTSX", "Фьючерсы", "default_research", "READY"),
    UniverseRow("NG@RTSX", "Фьючерсы", "default_research", "READY"),
    UniverseRow("Si@RTSX", "Фьючерсы", "default_research", "READY"),
    UniverseRow("SBER@MISX", "Акции", "default_research", "READY"),
    UniverseRow("GAZP@MISX", "Акции", "default_research", "READY"),
    UniverseRow("LKOH@MISX", "Акции", "default_research", "READY"),
    UniverseRow("USDRUB@CETS", "Валюта", "default_research", "READY"),
]


def ensure_schema() -> None:
    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS analytics_global_edge_universe_v2 (
                    id BIGSERIAL PRIMARY KEY,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    symbol TEXT NOT NULL,
                    asset_class TEXT NOT NULL,
                    source TEXT NOT NULL,
                    status TEXT NOT NULL,
                    UNIQUE(symbol, asset_class, source)
                );
                """
            )


def refresh_universe() -> int:
    ensure_schema()

    with psycopg2.connect(DB) as conn:
        with conn.cursor() as cur:
            saved = 0
            for row in DEFAULT_UNIVERSE:
                cur.execute(
                    """
                    INSERT INTO analytics_global_edge_universe_v2
                        (symbol, asset_class, source, status)
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (symbol, asset_class, source)
                    DO UPDATE SET
                        status = EXCLUDED.status,
                        created_at = now();
                    """,
                    (row.symbol, row.asset_class, row.source, row.status),
                )
                saved += 1
            return saved


def main() -> None:
    saved = refresh_universe()

    print("=== UNIVERSE_REFRESH_V1 ===")
    print("mode=research_only")
    print(f"universe_rows={saved}")
    print("asset_classes=Фьючерсы,Акции,Валюта")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("next=FEATURE_RECALC_V1")
    print("VERDICT=UNIVERSE_REFRESH_V1_READY")


if __name__ == "__main__":
    main()
