from __future__ import annotations

import json
import subprocess
from pathlib import Path


PHASE1_SCRIPT = Path(
    "src/scripts/analytics/build_runtime_rollout_phase1_shadow_v1.py"
)

ROLLOUT_CHECK_SCRIPT = Path(
    "src/scripts/analytics/build_edge_gate_runtime_rollout_check_v1.py"
)

SESSION_CONFIG = Path(
    "runtime/session_side_execution_gate_v1.json"
)

STRICT_CONFIG = Path(
    "runtime/edge_gate_strict_mode_v1.json"
)

DECAY_CONFIG = Path(
    "runtime/edge_gate_decay_state_v1.json"
)


def git_clean() -> bool:
    result = subprocess.run(
        ["git", "status", "--short"],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() == ""


def py_compile_ok() -> bool:
    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            "src/scripts/analytics/build_runtime_rollout_phase1_shadow_v1.py",
            "src/scripts/analytics/build_edge_gate_runtime_rollout_check_v1.py",
            "src/finam_core/execution/session_side_execution_gate_v1.py",
            "src/finam_core/execution/edge_gate_strict_mode_v1.py",
            "src/finam_core/analytics/edge_gate_pnl_decay_monitor_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def run_script(path: Path) -> tuple[bool, str]:
    result = subprocess.run(
        ["python", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0, result.stdout + result.stderr


def main() -> int:
    clean = git_clean()
    compile_ok = py_compile_ok()

    session_cfg = json.loads(
        SESSION_CONFIG.read_text(encoding="utf-8")
    )

    strict_cfg = json.loads(
        STRICT_CONFIG.read_text(encoding="utf-8")
    )

    decay_cfg = json.loads(
        DECAY_CONFIG.read_text(encoding="utf-8")
    )

    rollout_ok, rollout_output = run_script(
        ROLLOUT_CHECK_SCRIPT
    )

    phase1_ok, phase1_output = run_script(
        PHASE1_SCRIPT
    )

    rollout_ready = (
        rollout_ok
        and "status=ROLLOUT_READY" in rollout_output
    )

    phase1_ready = (
        phase1_ok
        and "status=PHASE1_READY" in phase1_output
    )

    allow_rows = len(
        session_cfg.get("allow", []) or []
    )

    block_rows = len(
        session_cfg.get("block", []) or []
    )

    insufficient_rows = len(
        session_cfg.get("insufficient_data", []) or []
    )

    runtime_windows = len(
        (decay_cfg.get("runtime_state") or {})
    )

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_COMPILE"
    elif not rollout_ready:
        status = "FAIL_ROLLOUT_NOT_READY"
    elif not phase1_ready:
        status = "FAIL_PHASE1_NOT_READY"
    else:
        status = "PHASE1_SHADOW_FINAL_READY"

    print(
        "RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_CHECK_V1",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"rollout_ready={rollout_ready}",
        f"phase1_ready={phase1_ready}",
        f"strict_enabled={strict_cfg.get('enabled')}",
        f"decay_enabled={decay_cfg.get('enabled')}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"runtime_windows={runtime_windows}",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_MODE",
        "mode=paper_shadow",
        "execution_blocking=false",
        "shadow_runtime=true",
        "fail_open=true",
        flush=True,
    )

    print(
        "RUNTIME_ROLLOUT_PHASE1_SHADOW_FINAL_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
