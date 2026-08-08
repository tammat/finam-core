#!/usr/bin/env python3
from __future__ import annotations

from collections import Counter
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.futures_monetary_validity_v1 import (
    classify_monetary_validity,
    load_monetary_rows,
)




def main() -> int:
    connection = psycopg2.connect(build_psycopg_url())

    try:
        connection.set_session(readonly=True)

        with connection.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            rows = load_monetary_rows(cursor)

        counts: Counter[str] = Counter()
        trade_counts: Counter[str] = Counter()
        ranking_allowed = 0

        for row in rows:
            status = classify_monetary_validity(row)
            counts[status] += 1
            trade_counts[status] += int(row["trades"] or 0)

            allowed = int(status == "VALID_MONETARY")
            ranking_allowed += allowed

            print(
                "LINEAGE_ROW "
                f"run_uuid={row['run_uuid']} "
                f"symbol={row['symbol']} "
                f"strategy={row['strategy_code']} "
                f"trades={row['trades']} "
                f"observed_multiplier="
                f"{row['observed_multiplier']} "
                f"exact_spec_multiplier="
                f"{row['exact_spec_multiplier']} "
                f"monetary_status={status} "
                f"ranking_allowed={allowed}"
            )

        print(
            "=== POSTGRESQL FUTURES "
            "MONETARY VALIDITY LINEAGE V1 ==="
        )
        print(f"total_runs={len(rows)}")

        for status in (
            "VALID_MONETARY",
            "LEGACY_INVALID_MONETARY",
            "UNRESOLVED_NO_SPEC",
            "UNRESOLVED_CBR_MONETARY",
            "NO_TRADES",
        ):
            print(
                f"{status.lower()}_runs="
                f"{counts[status]}"
            )
            print(
                f"{status.lower()}_trades="
                f"{trade_counts[status]}"
            )

        print(f"ranking_allowed_runs={ranking_allowed}")
        print("fail_closed=1")
        print("db_writes_performed=0")
        print("strategy_changed=0")
        print("risk_engine_changed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_MONETARY_VALIDITY_LINEAGE_V1_READY"
        )

        return 0

    finally:
        connection.close()


if __name__ == "__main__":
    raise SystemExit(main())
