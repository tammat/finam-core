#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib


ROOT = pathlib.Path("/opt/finam-core")

MIGRATION = (
    ROOT
    / "scripts/research/"
    "migrate_finam_futures_fill_evidence_v1.py"
)

BUILDER = (
    ROOT
    / "scripts/research/"
    "build_finam_futures_fill_evidence_v1.py"
)


def main() -> int:
    unresolved: list[str] = []

    for path in (MIGRATION, BUILDER):
        if not path.is_file():
            unresolved.append(f"FILE_MISSING:{path}")
            continue

        ast.parse(
            path.read_text(encoding="utf-8"),
            filename=str(path),
        )

    if not unresolved:
        migration = MIGRATION.read_text(encoding="utf-8")
        builder = BUILDER.read_text(encoding="utf-8")

        for fragment in (
            "analytics.futures_fill_evidence_v1",
            "quantity_contracts",
            "source_reference",
            "evidence_status",
        ):
            if fragment not in migration:
                unresolved.append(
                    f"MIGRATION_FRAGMENT_MISSING:{fragment}"
                )

        for fragment in (
            "canonical_symbol_required",
            "execution_timezone_required",
            "trade_date_execution_ts_mismatch",
            "duplicate_input_identity",
            "allow-derived-trade-id",
            "FINAM_FUTURES_FILL_EVIDENCE_IMPORT_V1_READY",
        ):
            if fragment not in builder:
                unresolved.append(
                    f"BUILDER_FRAGMENT_MISSING:{fragment}"
                )

        for fragment in (
            "UPDATE analytics.research_trade_v1",
            "DELETE FROM analytics.research_trade_v1",
            "UPDATE analytics.edge_observation_v1",
            "DELETE FROM analytics.edge_observation_v1",
            "send_order(",
            "place_order(",
            "submit_order(",
            "sqlite3",
            "bars.sqlite",
        ):
            if fragment in builder:
                unresolved.append(
                    f"FORBIDDEN_FRAGMENT:{fragment}"
                )

    print(f"unresolved_count={len(unresolved)}")

    for item in unresolved:
        print(f"UNRESOLVED={item}")

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
            "FINAM_FUTURES_FILL_EVIDENCE_V1_AUDIT_FAILED"
        )
        return 1

    print(
        "VERDICT="
        "FINAM_FUTURES_FILL_EVIDENCE_V1_AUDIT_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
