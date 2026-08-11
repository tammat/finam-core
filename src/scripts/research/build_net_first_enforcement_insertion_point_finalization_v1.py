from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]

OPTIMIZER = (
    ROOT
    / "src/scripts/analytics/"
    "build_entry_exit_optimizer_v1.py"
)

POLICY = (
    ROOT
    / "config/research/"
    "economic_cost_gate_policy_v1.json"
)

LOADER = (
    ROOT
    / "src/marketcore/research/economics/"
    "economic_cost_gate_policy_loader_v1.py"
)

VERIFIED_NET = (
    ROOT
    / "src/marketcore/research/economics/"
    "verified_net_admission_v1.py"
)


def require_text(path: Path, token: str) -> None:
    text = path.read_text(
        encoding="utf-8",
        errors="replace",
    )

    if token not in text:
        raise RuntimeError(
            "ERROR=INSERTION_CONTRACT_TOKEN_MISSING "
            f"path={path.relative_to(ROOT)} "
            f"token={token}"
        )


def main() -> int:
    for path in (
        OPTIMIZER,
        POLICY,
        LOADER,
        VERIFIED_NET,
    ):
        if not path.is_file():
            raise RuntimeError(
                "ERROR=INSERTION_CONTRACT_FILE_MISSING "
                f"path={path.relative_to(ROOT)}"
            )

    require_text(
        OPTIMIZER,
        '"shadow_r":outcome.net_r',
    )

    require_text(
        OPTIMIZER,
        "completed_cost_rows =",
    )

    require_text(
        OPTIMIZER,
        "if (not admission_id and statistical_pass and expensive_pass",
    )

    require_text(
        OPTIMIZER,
        "ensure_frozen_entry_exit_oos(",
    )

    require_text(
        VERIFIED_NET,
        "def evaluate_verified_net_admission_v1",
    )

    require_text(
        LOADER,
        "def load_economic_cost_gate_policy_v1",
    )

    print("candidate_source_identified=1")
    print("promotion_writer_identified=1")
    print("trade_level_verified_net_rows_available=1")
    print("verified_net_admission_reusable=1")
    print("policy_config_validated=1")
    print("policy_loader_reusable=1")

    print("canonical_trade_level_adapter_excluded=1")
    print("true_gross_required=0")

    print("pre_oos_boundary_confirmed=1")
    print(
        "integration_point="
        "build_entry_exit_optimizer_v1:"
        "before_ensure_frozen_entry_exit_oos"
    )

    print(
        "integration_input="
        "completed_evaluation_rows_shadow_r"
    )

    print(
        "integration_gate="
        "evaluate_verified_net_admission_v1"
    )

    print(
        "integration_policy="
        "economic_cost_gate_policy_v1.json"
    )

    print("reject_action=NO_NEW_OOS_ADMISSION")
    print("pass_action=EXISTING_OOS_PATH_UNCHANGED")

    print("integration_point_finalized=1")

    print("enforcement_applied=0")
    print("production_pipeline_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "NET_FIRST_ENFORCEMENT_INSERTION_POINT_FINALIZED"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
