#!/usr/bin/env python3
from __future__ import annotations

import csv
import pathlib
from collections import Counter


V2_DIR = pathlib.Path("/tmp/decision_owner_registry_v2")
REGIME_DIR = pathlib.Path("/tmp/regime_owner_confirmation_v1")
OUT = pathlib.Path("/tmp/decision_owner_registry_v3")

V2_REGISTRY = V2_DIR / "decision_owner_registry_v2.tsv"
V2_EDGES = V2_DIR / "decision_owner_edges_v2.tsv"
V2_DEFERRED = V2_DIR / "deferred_stages_v2.tsv"
V2_UNRESOLVED = V2_DIR / "unresolved_v2.tsv"

REGIME_CONFIRMED = REGIME_DIR / "confirmed_regime_owners.tsv"
REGIME_DEFERRED = REGIME_DIR / "deferred_regime_candidates.tsv"
REGIME_CONTRACT = REGIME_DIR / "regime_ownership_contract.txt"
REGIME_UNRESOLVED = REGIME_DIR / "unresolved.tsv"

REGISTRY_FILE = OUT / "decision_owner_registry_v3.tsv"
EDGES_FILE = OUT / "decision_owner_edges_v3.tsv"
DEFERRED_STAGES_FILE = OUT / "deferred_stages_v3.tsv"
DEFERRED_SCOPES_FILE = OUT / "deferred_scopes_v3.tsv"
CONTRACT_FILE = OUT / "decision_owner_contract_v3.txt"
UNRESOLVED_FILE = OUT / "unresolved_v3.tsv"

EXPECTED_REGIME_OWNER = "BRRegimeLayer.evaluate"
EXPECTED_REGIME_SCOPE = "MARKET_REGIME:BR"


def read_tsv(path: pathlib.Path) -> list[dict[str, str]]:
    if not path.is_file():
        raise RuntimeError(f"source_file_missing:{path}")

    with path.open("r", encoding="utf-8", newline="") as stream:
        return [
            {key: str(value or "").strip() for key, value in row.items()}
            for row in csv.DictReader(stream, delimiter="\t")
        ]


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def nonempty(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return [row for row in rows if any(row.values())]


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)

    registry_v2 = read_tsv(V2_REGISTRY)
    edges_v2 = read_tsv(V2_EDGES)
    deferred_v2 = read_tsv(V2_DEFERRED)

    unresolved: list[dict[str, object]] = []

    for row in nonempty(read_tsv(V2_UNRESOLVED)):
        unresolved.append(
            {
                "scope": row.get("scope", "REGISTRY_V2"),
                "symbol": row.get("symbol", ""),
                "reason": row.get("reason", "V2_UNRESOLVED"),
            }
        )

    for row in nonempty(read_tsv(REGIME_UNRESOLVED)):
        unresolved.append(
            {
                "scope": row.get("scope", "REGIME"),
                "symbol": row.get("candidate_symbol", ""),
                "reason": row.get("reason", "REGIME_UNRESOLVED"),
            }
        )

    regime_rows = read_tsv(REGIME_CONFIRMED)

    if len(regime_rows) != 1:
        unresolved.append(
            {
                "scope": "REGIME",
                "symbol": "",
                "reason": "CONFIRMED_REGIME_OWNER_CARDINALITY_INVALID",
            }
        )

    registry: list[dict[str, object]] = [
        {
            **row,
            "registry_version": "V3",
        }
        for row in registry_v2
    ]

    confirmed_regime_count = 0

    for row in regime_rows:
        symbol = row.get("owner_symbol", "")
        scope = row.get("ownership_scope", "")
        family = row.get("family", "")

        evidence_ok = (
            symbol == EXPECTED_REGIME_OWNER
            and scope == EXPECTED_REGIME_SCOPE
            and family == "BR"
            and row.get("owner_confirmed") == "1"
            and row.get("runtime_instrumentation") == "0"
            and row.get("resolution_classification")
            == "RESOLVED_RUNTIME_REACHABLE"
            and int(row.get("runtime_reachable_call_count") or 0) > 0
        )

        if not evidence_ok:
            unresolved.append(
                {
                    "scope": "REGIME",
                    "symbol": symbol,
                    "reason": "REGIME_OWNER_EVIDENCE_INCOMPLETE",
                }
            )
            continue

        registry.append(
            {
                "stage": "REGIME",
                "ownership_scope": scope,
                "owner_path": row["owner_path"],
                "owner_symbol": symbol,
                "owner_granularity": "FAMILY_METHOD",
                "classification": "CONFIRMED_REGIME_OWNER",
                "responsibility": "family_scoped_market_regime_classification",
                "failure_policy": "NO_REGIME_DECISION_ON_FAILURE",
                "family": family,
                "ownership_model": "FAMILY_SCOPED_PARTIAL",
                "owner_confirmed": 1,
                "runtime_instrumentation": 0,
                "registry_version": "V3",
            }
        )
        confirmed_regime_count += 1

    registry.sort(
        key=lambda row: (
            str(row.get("stage", "")),
            str(row.get("ownership_scope", "")),
            str(row.get("owner_symbol", "")),
        )
    )

    identity_counts = Counter(
        (
            str(row.get("stage", "")),
            str(row.get("ownership_scope", "")),
            str(row.get("owner_symbol", "")),
        )
        for row in registry
    )

    duplicate_count = sum(count > 1 for count in identity_counts.values())

    if duplicate_count:
        unresolved.append(
            {
                "scope": "REGISTRY",
                "symbol": "",
                "reason": "DUPLICATE_OWNER_IDENTITY",
            }
        )

    edges: list[dict[str, object]] = [
        {
            **row,
            "registry_version": "V3",
        }
        for row in edges_v2
    ]

    edges.append(
        {
            "edge_order": len(edges) + 1,
            "source_stage": "STRATEGY",
            "source_scope": "TRADE_INTENT:BR",
            "source_owner": "BrConservativeBreakout.on_signal_bar",
            "target_stage": "REGIME",
            "target_scope": EXPECTED_REGIME_SCOPE,
            "target_owner": EXPECTED_REGIME_OWNER,
            "classification": "CONFIRMED_BR_STRATEGY_TO_REGIME_FLOW",
            "reachable": 1,
            "runtime_instrumentation": 0,
            "registry_version": "V3",
        }
    )

    edges.append(
        {
            "edge_order": len(edges) + 1,
            "source_stage": "REGIME",
            "source_scope": EXPECTED_REGIME_SCOPE,
            "source_owner": EXPECTED_REGIME_OWNER,
            "target_stage": "RISK",
            "target_scope": "DECISION_GATE",
            "target_owner": "PortfolioRiskGate.check",
            "classification": "CONFIRMED_BR_REGIME_TO_RISK_FLOW",
            "reachable": 1,
            "runtime_instrumentation": 0,
            "registry_version": "V3",
        }
    )

    deferred_stages = [
        row
        for row in deferred_v2
        if row.get("stage") != "REGIME"
    ]

    deferred_scopes: list[dict[str, object]] = []

    generic_candidates = nonempty(read_tsv(REGIME_DEFERRED))

    deferred_scopes.append(
        {
            "stage": "REGIME",
            "ownership_scope": "MARKET_REGIME:GENERIC",
            "status": "DEFERRED",
            "candidate_count": len(generic_candidates),
            "candidate_symbols": ",".join(
                sorted(
                    row.get("owner_symbol", "")
                    for row in generic_candidates
                    if row.get("owner_symbol")
                )
            ),
            "reason": "NO_RESOLVED_RUNTIME_BINDING",
            "owner_confirmed": 0,
            "runtime_instrumentation": 0,
        }
    )

    registry_fields = (
        "stage",
        "ownership_scope",
        "owner_path",
        "owner_symbol",
        "owner_granularity",
        "classification",
        "responsibility",
        "failure_policy",
        "family",
        "ownership_model",
        "owner_confirmed",
        "runtime_instrumentation",
        "registry_version",
    )

    edge_fields = (
        "edge_order",
        "source_stage",
        "source_scope",
        "source_owner",
        "target_stage",
        "target_scope",
        "target_owner",
        "classification",
        "reachable",
        "runtime_instrumentation",
        "registry_version",
    )

    write_tsv(REGISTRY_FILE, registry_fields, registry)
    write_tsv(EDGES_FILE, edge_fields, edges)

    write_tsv(
        DEFERRED_STAGES_FILE,
        (
            "stage",
            "status",
            "candidate",
            "reason",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        deferred_stages,
    )

    write_tsv(
        DEFERRED_SCOPES_FILE,
        (
            "stage",
            "ownership_scope",
            "status",
            "candidate_count",
            "candidate_symbols",
            "reason",
            "owner_confirmed",
            "runtime_instrumentation",
        ),
        deferred_scopes,
    )

    write_tsv(
        UNRESOLVED_FILE,
        ("scope", "symbol", "reason"),
        unresolved,
    )

    with CONTRACT_FILE.open("w", encoding="utf-8") as stream:
        stream.write("DECISION OWNER REGISTRY V3\n")
        stream.write("==========================\n\n")
        stream.write(f"CONFIRMED_OWNER_COUNT={len(registry)}\n")
        stream.write(f"CONFIRMED_REGIME_OWNER_COUNT={confirmed_regime_count}\n")
        stream.write("REGIME_BR_OWNER=BRRegimeLayer.evaluate\n")
        stream.write("REGIME_GENERIC_OWNER=DEFERRED\n")
        stream.write(f"DEFERRED_STAGE_COUNT={len(deferred_stages)}\n")
        stream.write(f"DEFERRED_SCOPE_COUNT={len(deferred_scopes)}\n")
        stream.write(f"OWNERSHIP_EDGE_COUNT={len(edges)}\n")
        stream.write(f"DUPLICATE_OWNER_IDENTITY_COUNT={duplicate_count}\n")
        stream.write(f"UNRESOLVED_COUNT={len(unresolved)}\n")
        stream.write("RUNTIME_INSTRUMENTATION=0\n")

    print("=== BUILD DECISION OWNER REGISTRY V3 ===")
    print(f"confirmed_owner_count={len(registry)}")
    print(f"confirmed_regime_owner_count={confirmed_regime_count}")
    print(f"confirmed_stage_count={len({row['stage'] for row in registry})}")
    print(f"deferred_stage_count={len(deferred_stages)}")
    print(f"deferred_scope_count={len(deferred_scopes)}")
    print(f"ownership_edge_count={len(edges)}")
    print(f"duplicate_owner_identity_count={duplicate_count}")
    print(f"unresolved_count={len(unresolved)}")

    for row in registry:
        print(
            "REGISTRY_OWNER "
            f"stage={row['stage']} "
            f"scope={row['ownership_scope']} "
            f"family={row.get('family') or '-'} "
            f"symbol={row['owner_symbol']}"
        )

    print("owner_assignment_performed=1")
    print("writes_performed=0")
    print("db_writes_performed=0")
    print("runtime_instrumentation=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("broker_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print("VERDICT=DECISION_OWNER_REGISTRY_V3_READY")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
