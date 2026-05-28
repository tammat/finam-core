from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


SESSION_GATE_CONFIG = Path("runtime/session_side_execution_gate_v1.json")
STRICT_GATE_CONFIG = Path("runtime/edge_gate_strict_mode_v1.json")
PIPELINE_PATH = Path("src/finam_core/pipelines/paper_pipeline.py")


AUDIT_SQL = """
SELECT
    count(*) AS audit_total_events,
    count(*) FILTER (WHERE allowed = true) AS audit_allowed_events,
    count(*) FILTER (WHERE allowed = false) AS audit_blocked_events,
    count(*) FILTER (WHERE source ILIKE '%test%') AS audit_test_events,
    count(*) FILTER (WHERE raw_json::text ILIKE '%test%') AS audit_raw_test_events,
    max(created_at) AS audit_last_event_ts
FROM session_side_gate_runtime_audit_v1;
"""


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
            "src/finam_core/execution/session_side_gate_runtime_audit_v1.py",
            "src/finam_core/execution/edge_gate_strict_mode_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    session_config = json.loads(SESSION_GATE_CONFIG.read_text(encoding="utf-8"))
    strict_config = json.loads(STRICT_GATE_CONFIG.read_text(encoding="utf-8"))
    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    allow_rows = len(session_config.get("allow", []) or [])
    block_rows = len(session_config.get("block", []) or [])
    insufficient_rows = len(session_config.get("insufficient_data", []) or [])

    strict_enabled = bool(strict_config.get("enabled"))
    strict_threshold = float(strict_config.get("strict_expectancy_threshold", 0.0))
    strict_min_closed = int(strict_config.get("strict_min_closed_trades", 0))

    has_session_gate = "SessionSideExecutionGateV1" in pipeline
    has_session_audit = "SessionSideGateRuntimeAuditV1" in pipeline
    has_strict_gate = "EdgeGateStrictModeV1" in pipeline
    has_session_block_log = "PIPE_SESSION_SIDE_GATE_BLOCK" in pipeline
    has_strict_log = "PIPE_EDGE_GATE_STRICT_MODE" in pipeline
    has_strict_fail_open = "PIPE_EDGE_GATE_STRICT_MODE_FAILED_OPEN" in pipeline

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(AUDIT_SQL)
            audit = dict(cur.fetchone())

    clean = git_clean()
    compile_ok = py_compile_ok()

    status = "PRODUCTION_READY"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not compile_ok:
        status = "FAIL_PY_COMPILE"
    elif allow_rows <= 0:
        status = "FAIL_NO_ALLOW_WINDOWS"
    elif block_rows <= 0:
        status = "FAIL_NO_BLOCK_WINDOWS"
    elif not strict_enabled:
        status = "FAIL_STRICT_MODE_DISABLED"
    elif int(audit["audit_test_events"] or 0) > 0:
        status = "WARN_TEST_AUDIT_ROWS"
    elif int(audit["audit_raw_test_events"] or 0) > 0:
        status = "WARN_RAW_TEST_AUDIT_ROWS"
    elif not all([
        has_session_gate,
        has_session_audit,
        has_strict_gate,
        has_session_block_log,
        has_strict_log,
        has_strict_fail_open,
    ]):
        status = "FAIL_PIPELINE_WIRING"

    print("EDGE_GATE_PRODUCTION_STATUS_V1", flush=True)

    print(
        "EDGE_GATE_PRODUCTION_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_ok}",
        f"session_config_exists={SESSION_GATE_CONFIG.exists()}",
        f"strict_config_exists={STRICT_GATE_CONFIG.exists()}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"strict_enabled={strict_enabled}",
        f"strict_threshold={strict_threshold}",
        f"strict_min_closed_trades={strict_min_closed}",
        flush=True,
    )

    print(
        "EDGE_GATE_PRODUCTION_WIRING",
        f"has_session_gate={has_session_gate}",
        f"has_session_audit={has_session_audit}",
        f"has_strict_gate={has_strict_gate}",
        f"has_session_block_log={has_session_block_log}",
        f"has_strict_log={has_strict_log}",
        f"has_strict_fail_open={has_strict_fail_open}",
        flush=True,
    )

    print(
        "EDGE_GATE_PRODUCTION_AUDIT",
        f"audit_total_events={audit['audit_total_events']}",
        f"audit_allowed_events={audit['audit_allowed_events']}",
        f"audit_blocked_events={audit['audit_blocked_events']}",
        f"audit_test_events={audit['audit_test_events']}",
        f"audit_raw_test_events={audit['audit_raw_test_events']}",
        f"audit_last_event_ts={audit['audit_last_event_ts']}",
        flush=True,
    )

    print(
        "EDGE_GATE_PRODUCTION_STATUS_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
