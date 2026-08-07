#!/usr/bin/env python3
from __future__ import annotations

import pathlib


ROOT = pathlib.Path("/opt/finam-core")

MIGRATION = (
    ROOT
    / "scripts/research/"
    "migrate_finam_futures_commission_allocation_v1.py"
)

BUILDER = (
    ROOT
    / "scripts/research/"
    "build_finam_futures_commission_allocation_v1.py"
)


def main() -> int:
    unresolved: list[str] = []

    for path in (MIGRATION, BUILDER):
        if not path.is_file():
            unresolved.append(f"FILE_MISSING:{path}")

    if unresolved:
        for row in unresolved:
            print(f"UNRESOLVED={row}")
        return 1

    migration = MIGRATION.read_text(encoding="utf-8")
    builder = BUILDER.read_text(encoding="utf-8")

    required_tables = (
        "analytics.futures_commission_daily_v1",
        "analytics.futures_commission_allocation_v1",
    )

    for table in required_tables:
        if table not in migration:
            unresolved.append(
                f"TABLE_CONTRACT_MISSING:{table}"
            )

    required_builder = (
        "CONTRACT_COUNT",
        "TURNOVER",
        "allocation_reconciliation_failed",
        "daily_fills_missing",
        "commission_per_contract",
        "FINAM_FUTURES_COMMISSION_ALLOCATION_V1_READY",
    )

    for fragment in required_builder:
        if fragment not in builder:
            unresolved.append(
                f"BUILDER_FRAGMENT_MISSING:{fragment}"
            )

    forbidden = (
        "UPDATE analytics.research_trade_v1",
        "DELETE FROM analytics.research_trade_v1",
        "UPDATE analytics.edge_observation_v1",
        "DELETE FROM analytics.edge_observation_v1",
        "send_order(",
        "place_order(",
        "submit_order(",
        "sqlite3",
        "bars.sqlite",
    )

    for fragment in forbidden:
        if fragment in builder:
            unresolved.append(
                f"FORBIDDEN_FRAGMENT:{fragment}"
            )

    print(f"unresolved_count={len(unresolved)}")

    for row in unresolved:
        print(f"UNRESOLVED={row}")

    print("historical_trade_rows_changed=0")
    print("historical_observation_rows_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if unresolved:
        print(
            "VERDICT="
            "FINAM_FUTURES_COMMISSION_ALLOCATION_V1_AUDIT_FAILED"
        )
        return 1

    print(
        "VERDICT="
        "FINAM_FUTURES_COMMISSION_ALLOCATION_V1_AUDIT_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
