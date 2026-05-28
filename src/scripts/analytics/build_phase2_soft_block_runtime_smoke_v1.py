from __future__ import annotations

import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo

from finam_core.execution.runtime_edge_governance_soft_block_v1 import (
    RuntimeEdgeGovernanceSoftBlockV1,
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
            "src/scripts/analytics/build_phase2_soft_block_runtime_smoke_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    runtime = RuntimeEdgeGovernanceSoftBlockV1()

    allow = runtime.decide(
        symbol="BR_ROLLING@RTSX",
        side="BUY",
        ts=datetime(2026, 5, 28, 8, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    block = runtime.decide(
        symbol="BR_ROLLING@RTSX",
        side="BUY",
        ts=datetime(2026, 5, 28, 19, 0, tzinfo=ZoneInfo("Europe/Moscow")),
    )

    status = "PHASE2_RUNTIME_SMOKE_READY"

    if not git_clean():
        status = "WARN_GIT_DIRTY"
    elif not py_compile_ok():
        status = "FAIL_PY_COMPILE"
    elif allow.allowed is not True:
        status = "FAIL_ALLOW_CASE"
    elif block.allowed is not False:
        status = "FAIL_BLOCK_CASE"

    print("PHASE2_RUNTIME_SOFT_BLOCK_SMOKE_V1", flush=True)

    print(
        "PHASE2_RUNTIME_SOFT_BLOCK_ALLOW",
        f"allowed={allow.allowed}",
        f"action={allow.action}",
        f"reason={allow.reason}",
        f"hour_msk={allow.hour_msk}",
        f"expectancy_points={allow.expectancy_points}",
        flush=True,
    )

    print(
        "PHASE2_RUNTIME_SOFT_BLOCK_BLOCK",
        f"allowed={block.allowed}",
        f"action={block.action}",
        f"reason={block.reason}",
        f"hour_msk={block.hour_msk}",
        f"expectancy_points={block.expectancy_points}",
        flush=True,
    )

    print(
        "PHASE2_RUNTIME_SOFT_BLOCK_STATUS",
        f"status={status}",
        f"git_clean={git_clean()}",
        f"py_compile_ok={py_compile_ok()}",
        flush=True,
    )

    print(
        "PHASE2_RUNTIME_SOFT_BLOCK_SMOKE_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
