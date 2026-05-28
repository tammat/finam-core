from __future__ import annotations

import subprocess
from pathlib import Path


CHECKS = [
    (
        "phase2_production_status",
        "src/scripts/analytics/build_phase2_soft_block_production_status_v1.py",
        "status=PHASE2_PRODUCTION_READY",
    ),
    (
        "phase2_pipeline_final",
        "src/scripts/analytics/build_phase2_soft_block_pipeline_final_check_v1.py",
        "status=PHASE2_PIPELINE_READY",
    ),
    (
        "phase2_runtime_smoke",
        "src/scripts/analytics/build_phase2_soft_block_runtime_smoke_v1.py",
        "status=PHASE2_RUNTIME_SMOKE_READY",
    ),
    (
        "runtime_rollout",
        "src/scripts/analytics/build_edge_gate_runtime_rollout_check_v1.py",
        "status=ROLLOUT_READY",
    ),
    (
        "live_observation",
        "src/scripts/analytics/build_phase2_soft_block_live_observation_v1.py",
        "PHASE2_SOFT_BLOCK_LIVE_OBSERVATION_V1_OK",
    ),
]


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def run_check(name: str, script: str, expected: str) -> tuple[bool, str]:
    result = subprocess.run(
        ["python", script],
        capture_output=True,
        text=True,
        check=False,
    )

    output = result.stdout + result.stderr
    ok = result.returncode == 0 and expected in output

    print(
        "RUNTIME_GOVERNANCE_STAGE_CHECK_ROW",
        f"name={name}",
        f"ok={ok}",
        f"expected={expected}",
        flush=True,
    )

    return ok, output


def main() -> int:
    print("RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1", flush=True)

    py_compile = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            "src/finam_core/execution/runtime_edge_governance_soft_block_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
            "src/scripts/analytics/build_runtime_governance_stage_final_check_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    compile_ok = py_compile.returncode == 0
    clean = git_clean()

    passed = 0
    failed = 0

    for name, script, expected in CHECKS:
        if not Path(script).exists():
            print(
                "RUNTIME_GOVERNANCE_STAGE_CHECK_ROW",
                f"name={name}",
                "ok=False",
                "reason=script_missing",
                flush=True,
            )
            failed += 1
            continue

        ok, _ = run_check(name, script, expected)

        if ok:
            passed += 1
        else:
            failed += 1

    status = "RUNTIME_GOVERNANCE_STAGE_COMPLETE"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_COMPILE"
    elif failed > 0:
        status = "FAIL_STAGE_CHECKS"

    print(
        "RUNTIME_GOVERNANCE_STAGE_FINAL_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"passed={passed}",
        f"failed={failed}",
        flush=True,
    )

    print(
        "RUNTIME_GOVERNANCE_STAGE_FINAL_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0 if status in {"RUNTIME_GOVERNANCE_STAGE_COMPLETE", "WARN_GIT_DIRTY"} else 1


if __name__ == "__main__":
    raise SystemExit(main())
