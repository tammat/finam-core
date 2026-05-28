from __future__ import annotations

import json
import subprocess
from pathlib import Path


PRODUCTION_STATUS_SCRIPT = Path(
    "src/scripts/analytics/build_edge_gate_production_status_v1.py"
)

DECAY_FINAL_SCRIPT = Path(
    "src/scripts/analytics/build_edge_gate_decay_final_check_v1.py"
)

SESSION_GATE_CONFIG = Path(
    "runtime/session_side_execution_gate_v1.json"
)

STRICT_CONFIG = Path(
    "runtime/edge_gate_strict_mode_v1.json"
)

DECAY_CONFIG = Path(
    "runtime/edge_gate_decay_state_v1.json"
)

PIPELINE_PATH = Path(
    "src/finam_core/pipelines/paper_pipeline.py"
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
    session_cfg = json.loads(
        SESSION_GATE_CONFIG.read_text(encoding="utf-8")
    )

    strict_cfg = json.loads(
        STRICT_CONFIG.read_text(encoding="utf-8")
    )

    decay_cfg = json.loads(
        DECAY_CONFIG.read_text(encoding="utf-8")
    )

    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    clean = git_clean()
    compile_ok = py_compile_ok()

    prod_ok, prod_output = run_script(PRODUCTION_STATUS_SCRIPT)
    decay_ok, decay_output = run_script(DECAY_FINAL_SCRIPT)

    production_ready = (
        "status=PRODUCTION_READY" in prod_output
    )

    decay_ready = (
        "EDGE_GATE_DECAY_FINAL_CHECK_V1_OK status=OK"
        in decay_output
    )

    has_session_gate = (
        "_check_session_side_execution_gate_v1"
        in pipeline
    )

    has_strict_gate = (
        "EdgeGateStrictModeV1"
        in pipeline
    )

    has_decay_monitor = Path(
        "src/finam_core/analytics/edge_gate_pnl_decay_monitor_v1.py"
    ).exists()

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
        decay_cfg.get("runtime_state", {}) or {}
    )

    strict_enabled = bool(
        strict_cfg.get("enabled")
    )

    decay_enabled = bool(
        decay_cfg.get("enabled")
    )

    status = "ROLLOUT_READY"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_PY_COMPILE"
    elif not production_ready:
        status = "FAIL_PRODUCTION_STATUS"
    elif not decay_ready:
        status = "FAIL_DECAY_CHECK"
    elif not strict_enabled:
        status = "FAIL_STRICT_DISABLED"
    elif not decay_enabled:
        status = "FAIL_DECAY_DISABLED"
    elif not has_session_gate:
        status = "FAIL_SESSION_GATE_MISSING"
    elif not has_strict_gate:
        status = "FAIL_STRICT_GATE_MISSING"
    elif not has_decay_monitor:
        status = "FAIL_DECAY_MONITOR_MISSING"

    print("EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1", flush=True)

    print(
        "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"production_ready={production_ready}",
        f"decay_ready={decay_ready}",
        f"strict_enabled={strict_enabled}",
        f"decay_enabled={decay_enabled}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"runtime_windows={runtime_windows}",
        flush=True,
    )

    print(
        "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_WIRING",
        f"has_session_gate={has_session_gate}",
        f"has_strict_gate={has_strict_gate}",
        f"has_decay_monitor={has_decay_monitor}",
        flush=True,
    )

    print(
        "EDGE_GATE_RUNTIME_ROLLOUT_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
