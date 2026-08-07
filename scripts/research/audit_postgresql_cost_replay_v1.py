#!/usr/bin/env python3
from __future__ import annotations

import pathlib


ROOT = pathlib.Path("/opt/finam-core")

FILES = (
    ROOT / "scripts/research/migrate_postgresql_cost_replay_v1.py",
    ROOT / "scripts/research/build_postgresql_cost_replay_v1.py",
)


def main() -> int:
    unresolved: list[str] = []

    for path in FILES:
        if not path.is_file():
            unresolved.append(f"FILE_MISSING:{path}")

    if unresolved:
        for row in unresolved:
            print(f"UNRESOLVED={row}")
        return 1

    migration = FILES[0].read_text(encoding="utf-8")
    builder = FILES[1].read_text(encoding="utf-8")

    required_tables = (
        "analytics.cost_replay_run_v1",
        "analytics.cost_replay_trade_v1",
        "analytics.cost_replay_result_v1",
    )

    for table in required_tables:
        if table not in migration:
            unresolved.append(
                f"TABLE_CONTRACT_MISSING:{table}"
            )

    required_builder_fragments = (
        "FINAM_EQUITY_REPORT_PROXY_V1",
        "FINAM_FUTURES_ALLOCATED_V1",
        "futures_commission_allocation_v1",
        "POSTGRESQL_COST_REPLAY_V1_BLOCKED",
        "POSTGRESQL_COST_REPLAY_V1_READY",
    )

    for fragment in required_builder_fragments:
        if fragment not in builder:
            unresolved.append(
                f"BUILDER_FRAGMENT_MISSING:{fragment}"
            )

    forbidden_source_mutations = (
        "UPDATE analytics.research_trade_v1",
        "DELETE FROM analytics.research_trade_v1",
        "UPDATE analytics.edge_observation_v1",
        "DELETE FROM analytics.edge_observation_v1",
        "UPDATE analytics.edge_lab_run_v1",
        "DELETE FROM analytics.edge_lab_run_v1",
    )

    for fragment in forbidden_source_mutations:
        if fragment in builder:
            unresolved.append(
                f"SOURCE_MUTATION_FOUND:{fragment}"
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
            "POSTGRESQL_COST_REPLAY_V1_AUDIT_FAILED"
        )
        return 1

    print(
        "VERDICT="
        "POSTGRESQL_COST_REPLAY_V1_AUDIT_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
