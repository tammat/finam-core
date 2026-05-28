from __future__ import annotations

import json
import subprocess
from pathlib import Path


STRICT_CONFIG_PATH = Path("runtime/edge_gate_strict_mode_v1.json")
SESSION_GATE_CONFIG_PATH = Path("runtime/session_side_execution_gate_v1.json")
PIPELINE_PATH = Path("src/finam_core/pipelines/paper_pipeline.py")


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
            "src/finam_core/execution/edge_gate_strict_mode_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    strict_config = json.loads(STRICT_CONFIG_PATH.read_text(encoding="utf-8"))
    session_config = json.loads(SESSION_GATE_CONFIG_PATH.read_text(encoding="utf-8"))
    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    clean = git_clean()
    compile_ok = py_compile_ok()

    enabled = bool(strict_config.get("enabled"))
    threshold = float(strict_config.get("strict_expectancy_threshold", 0.0))
    min_closed = int(strict_config.get("strict_min_closed_trades", 0))

    allow_rows = len(session_config.get("allow", []) or [])
    block_rows = len(session_config.get("block", []) or [])
    insufficient_rows = len(session_config.get("insufficient_data", []) or [])

    has_import = "EdgeGateStrictModeV1" in pipeline
    has_runtime_log = "PIPE_EDGE_GATE_STRICT_MODE" in pipeline
    has_failed_open_log = "PIPE_EDGE_GATE_STRICT_MODE_FAILED_OPEN" in pipeline
    has_init = "self.edge_gate_strict_mode_v1 = EdgeGateStrictModeV1(" in pipeline

    status = "OK"
    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_PY_COMPILE"
    elif not enabled:
        status = "FAIL_STRICT_DISABLED"
    elif allow_rows <= 0:
        status = "FAIL_NO_ALLOW_ROWS"
    elif block_rows <= 0:
        status = "FAIL_NO_BLOCK_ROWS"
    elif not all([has_import, has_runtime_log, has_failed_open_log, has_init]):
        status = "FAIL_PIPELINE_WIRING"

    print("EDGE_GATE_STRICT_MODE_FINAL_CHECK_V1", flush=True)
    print(
        "EDGE_GATE_STRICT_MODE_FINAL_CHECK_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"strict_config_exists={STRICT_CONFIG_PATH.exists()}",
        f"enabled={enabled}",
        f"threshold={threshold}",
        f"min_closed_trades={min_closed}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        flush=True,
    )

    print(
        "EDGE_GATE_STRICT_MODE_FINAL_CHECK_WIRING",
        f"has_import={has_import}",
        f"has_init={has_init}",
        f"has_runtime_log={has_runtime_log}",
        f"has_failed_open_log={has_failed_open_log}",
        flush=True,
    )

    print(
        "EDGE_GATE_STRICT_MODE_FINAL_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
