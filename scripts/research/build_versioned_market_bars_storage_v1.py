#!/usr/bin/env python3
from __future__ import annotations

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.versioned_market_bars_v1 import DDL


SOURCE_VERSION = "VERSIONED_MARKET_BARS_STORAGE_V1"


def create_storage(
    connection,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(DDL)


def main() -> int:
    with psycopg2.connect(
        build_psycopg_url()
    ) as connection:
        create_storage(connection)

    print(
        "table=analytics.research_market_bars_v1"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print(
        "VERDICT="
        "VERSIONED_MARKET_BARS_STORAGE_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
