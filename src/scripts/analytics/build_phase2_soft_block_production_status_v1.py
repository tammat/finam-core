from __future__ import annotations

import json
import subprocess
from pathlib import Path


SESSION_GATE_PATH = Path(
    "runtime/session_side_execution_gate_v1.json"
)

DECAY_STATE_PATH = Path(
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
            "src/finam_core/execution/runtime_edge_governance_soft_block_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
            "src/scripts/analytics/build_phase2_soft_block_production_status_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    session_cfg = json.loads(
        SESSION_GATE_PATH.read_text(encoding="utf-8")
    )

    decay_cfg = json.loads(
        DECAY_STATE_PATH.read_text(encoding="utf-8")
    )

    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    allow_rows = len(session_cfg.get("allow", []) or [])
    block_rows = len(session_cfg.get("block", []) or [])
    insufficient_rows = len(
        session_cfg.get("insufficient_data", []) or []
    )

    runtime_windows = len(
        (decay_cfg.get("runtime_state") or {})
    )

    healthy_windows = 0
    decay_windows = 0

    for row in (
        decay_cfg.get("runtime_state", {}) or {}
    ).values():
        expectancy = float(
            row.get("expectancy_points", 0.0)
        )

        if expectancy > 0:
            healthy_windows += 1
        else:
            decay_windows += 1

    has_phase2_decision = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION"
        in pipeline
    )

    has_soft_block = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK"
        in pipeline
    )

    has_fail_open = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_FAILED_OPEN"
        in pipeline
    )

    production_ready = (
        git_clean()
        and py_compile_ok()
        and has_phase2_decision
        and has_soft_block
        and has_fail_open
        and healthy_windows >= 1
    )

    status = (
        "PHASE2_PRODUCTION_READY"
        if production_ready
        else "WARN_GIT_DIRTY"
    )

    print(
        "PHASE2_SOFT_BLOCK_PRODUCTION_STATUS_V1",
        flush=True,
    )

    print(
        "PHASE2_SOFT_BLOCK_PRODUCTION_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"py_compile_ok={py_compile_ok()}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"runtime_windows={runtime_windows}",
        f"healthy_windows={healthy_windows}",
        f"decay_windows={decay_windows}",
        f"has_phase2_decision={has_phase2_decision}",
        f"has_soft_block={has_soft_block}",
        f"has_fail_open={has_fail_open}",
        f"production_ready={production_ready}",
        flush=True,
    )

    print(
        "PHASE2_SOFT_BLOCK_PRODUCTION_STATUS_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
