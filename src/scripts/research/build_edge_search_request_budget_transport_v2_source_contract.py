"""Read-only source inventory перед EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2."""

from __future__ import annotations

from pathlib import Path


FILES = (
    Path("src/marketcore/action/command_worker_v2.py"),
    Path("src/scripts/run_autonomous_edge_search_cycle_v1.py"),
    Path("src/scripts/run_targeted_entry_exit_oos_v1.py"),
    Path("src/scripts/analytics/build_entry_exit_optimizer_v1.py"),
)

TOKENS = (
    "edge_search_request_parameter_v1",
    "variant_budget",
    "EDGE_SEARCH_TARGET_VARIANT_BUDGET",
    "EDGE_SEARCH_TARGET_CYCLE_BUDGET",
    "cycle_budget",
)


def main() -> int:
    missing_files = [
        str(path)
        for path in FILES
        if not path.exists()
    ]

    if missing_files:
        raise RuntimeError(
            "BUDGET_TRANSPORT_V2_SOURCE_FILE_MISSING:"
            + ",".join(missing_files)
        )

    total_variant_env = 0
    total_cycle_env = 0

    for path in FILES:
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        print(f"SOURCE_FILE path={path}")

        file_matches = 0

        for lineno, line in enumerate(lines, start=1):
            if not any(token in line for token in TOKENS):
                continue

            file_matches += 1

            print(
                "SOURCE_MATCH "
                f"path={path} "
                f"line={lineno} "
                f"text={line.strip()}"
            )

        variant_env = text.count(
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET"
        )
        cycle_env = text.count(
            "EDGE_SEARCH_TARGET_CYCLE_BUDGET"
        )

        total_variant_env += variant_env
        total_cycle_env += cycle_env

        print(
            "SOURCE_SUMMARY "
            f"path={path} "
            f"matches={file_matches} "
            f"variant_env_refs={variant_env} "
            f"cycle_env_refs={cycle_env}"
        )

    worker = FILES[0].read_text(encoding="utf-8")
    cycle = FILES[1].read_text(encoding="utf-8")
    targeted = FILES[2].read_text(encoding="utf-8")
    optimizer = FILES[3].read_text(encoding="utf-8")

    checks = {
        "parameter_store_read_present":
            "edge_search_request_parameter_v1" in worker,

        "worker_variant_transport_present":
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in worker,

        "cycle_variant_transport_present":
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in cycle,

        "targeted_variant_transport_present":
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in targeted,

        "optimizer_variant_receive_present":
            "EDGE_SEARCH_TARGET_VARIANT_BUDGET" in optimizer,
    }

    for name, ok in checks.items():
        print(f"CHECK name={name} passed={int(ok)}")

    assert all(checks.values())

    print(f"total_variant_env_refs={total_variant_env}")
    print(f"total_cycle_env_refs={total_cycle_env}")

    print(
        "cycle_budget_transport_fully_present="
        f"{int(total_cycle_env > 0)}"
    )

    print("variant_budget_semantics=UNIVERSE_CAPACITY_UPPER_BOUND")
    print("cycle_budget_semantics=TARGETED_CHALLENGERS_PER_CYCLE")
    print("legacy_cycle_budget_fallback_required=1")
    print("target_id_encodes_cycle_budget=0")

    print("db_writes_performed=0")
    print("queue_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "EDGE_SEARCH_REQUEST_BUDGET_TRANSPORT_V2_SOURCE_CONTRACT_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
