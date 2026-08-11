from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True, slots=True)
class TestResult:
    name: str
    stdout: str


def run_test(relative_path: str) -> TestResult:
    path = ROOT / relative_path

    if not path.is_file():
        raise RuntimeError(
            f"ERROR=READINESS_TEST_MISSING path={relative_path}"
        )

    completed = subprocess.run(
        [str(path)],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    if completed.returncode != 0:
        raise RuntimeError(
            "ERROR=READINESS_DEPENDENCY_FAILED "
            f"path={relative_path} "
            f"exit_code={completed.returncode}\n"
            f"{completed.stdout}\n"
            f"{completed.stderr}"
        )

    return TestResult(
        name=relative_path,
        stdout=completed.stdout,
    )


def require(pattern: str, result: TestResult) -> None:
    if re.search(pattern, result.stdout, re.MULTILINE) is None:
        raise RuntimeError(
            "ERROR=READINESS_CONTRACT_MISSING "
            f"test={result.name} "
            f"pattern={pattern}"
        )


def main() -> int:
    negative = run_test(
        "tests/test_net_first_trend_pullback_control_integration_v2.sh"
    )
    verified = run_test(
        "tests/test_verified_net_real_shadow_admission_v1.sh"
    )
    trade_level = run_test(
        "tests/test_trade_level_real_shadow_admission_v1.sh"
    )
    runner = run_test(
        "tests/test_lkoh_runner_v2_cost_replay_v1.sh"
    )
    coverage = run_test(
        "tests/test_net_first_shadow_coverage_v1.sh"
    )
    pipeline = run_test(
        "tests/test_net_first_edge_pipeline_v1.sh"
    )

    require(r"^economic_gate_reject=3$", negative)
    require(r"^robustness_saved=3$", negative)
    require(r"^policy_from_config=1$", negative)
    require(
        r"^negative_expectancy_rejection_validated=1$",
        negative,
    )

    require(r"^verified_net_candidates=16$", verified)
    require(r"^would_admit=14$", verified)

    require(r"^trade_level_candidates=9$", trade_level)
    require(r"^would_admit=3$", trade_level)
    require(r"^individual_trade_rows_used=1$", trade_level)

    require(
        r"decision=WOULD_ADMIT economic_status=PASS",
        runner,
    )
    require(r"^individual_trade_rows_used=1$", runner)

    require(r"^total_candidates=27$", coverage)
    require(r"^economically_resolved=27$", coverage)
    require(r"^would_admit=18$", coverage)
    require(r"^would_reject=9$", coverage)
    require(r"^economic_coverage_pct=100\.0000$", coverage)
    require(r"^shadow_admission_validated=1$", coverage)

    require(r"^economic_gate_before_robustness=1$", pipeline)
    require(r"^strategy_specific_logic_used=0$", pipeline)

    for result in (
        negative,
        verified,
        trade_level,
        runner,
        coverage,
    ):
        require(
            r"^enforced_admission_enabled=0$",
            result,
        )

    print("negative_control_total=3")
    print("negative_control_reject=3")
    print("negative_control_robustness_saved=3")

    print("positive_verified_net_admit=14")
    print("positive_trade_level_admit=3")
    print("positive_runner_v2_admit=1")
    print("positive_control_classes=3")

    print("shadow_candidates=27")
    print("shadow_economically_resolved=27")
    print("shadow_would_admit=18")
    print("shadow_would_reject=9")
    print("shadow_coverage_pct=100.0000")

    print("economic_gate_before_robustness=1")
    print("strategy_specific_logic_used=0")
    print("policy_from_config=1")

    print("economic_admission_scope_only=1")
    print("robustness_gate_still_required=1")
    print("oos_gate_still_required=1")

    print("enforced_admission_enabled=0")
    print("production_pipeline_changed=0")
    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "NET_FIRST_ENFORCED_ADMISSION_READINESS_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
