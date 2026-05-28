from __future__ import annotations

import subprocess
from pathlib import Path


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
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    has_import = (
        "RuntimeEdgeGovernanceSoftBlockV1"
        in pipeline
    )

    has_init = (
        "self.runtime_edge_governance_soft_block_v1 = RuntimeEdgeGovernanceSoftBlockV1()"
        in pipeline
    )

    has_decision_log = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION"
        in pipeline
    )

    has_soft_block_log = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK"
        in pipeline
    )

    has_failed_open_log = (
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_FAILED_OPEN"
        in pipeline
    )

    risk_reject_pos = pipeline.find("PIPE_RISK_REJECT")

    risk_router_pos = pipeline.rfind(
        "decision = self.risk_router.route(",
        0,
        risk_reject_pos,
    )

    phase2_pos = pipeline.rfind(
        "PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION",
        0,
        risk_router_pos,
    )

    session_gate_pos = pipeline.rfind(
        "if not self._check_session_side_execution_gate_v1(",
        0,
        risk_router_pos,
    )

    order_ok = (
        phase2_pos != -1
        and session_gate_pos != -1
        and risk_router_pos != -1
        and risk_reject_pos != -1
        and phase2_pos < session_gate_pos < risk_router_pos < risk_reject_pos
    )

    clean = git_clean()
    compile_ok = py_compile_ok()

    status = "PHASE2_PIPELINE_READY"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_COMPILE"
    elif not has_import:
        status = "FAIL_IMPORT"
    elif not has_init:
        status = "FAIL_INIT"
    elif not has_decision_log:
        status = "FAIL_DECISION_LOG"
    elif not has_soft_block_log:
        status = "FAIL_SOFT_BLOCK_LOG"
    elif not has_failed_open_log:
        status = "FAIL_FAILED_OPEN_LOG"
    elif not order_ok:
        status = "FAIL_ORDER"

    print(
        "PHASE2_SOFT_BLOCK_PIPELINE_FINAL_CHECK_V1",
        flush=True,
    )

    print(
        "PHASE2_SOFT_BLOCK_PIPELINE_FINAL_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"has_import={has_import}",
        f"has_init={has_init}",
        f"has_decision_log={has_decision_log}",
        f"has_soft_block_log={has_soft_block_log}",
        f"has_failed_open_log={has_failed_open_log}",
        f"order_ok={order_ok}",
        flush=True,
    )

    print(
        "PHASE2_SOFT_BLOCK_PIPELINE_FINAL_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
