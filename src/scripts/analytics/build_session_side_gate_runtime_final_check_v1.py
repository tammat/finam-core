from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url


GATE_CONFIG_PATH = Path("runtime/session_side_execution_gate_v1.json")
PIPELINE_PATH = Path("src/finam_core/pipelines/paper_pipeline.py")


AUDIT_SQL = """
SELECT
    count(*) AS total_events,
    count(*) FILTER (WHERE allowed = true) AS allowed_events,
    count(*) FILTER (WHERE allowed = false) AS blocked_events,
    count(*) FILTER (WHERE source ILIKE '%test%') AS test_events,
    count(*) FILTER (WHERE raw_json::text ILIKE '%test%') AS raw_test_events,
    max(created_at) AS last_event_ts
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


def compile_ok() -> bool:
    result = subprocess.run(
        [
            "python",
            "-m",
            "py_compile",
            "src/finam_core/execution/session_side_execution_gate_v1.py",
            "src/finam_core/execution/session_side_gate_runtime_audit_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
            "src/scripts/analytics/build_session_side_gate_final_healthcheck_v1.py",
            "src/scripts/analytics/build_session_side_gate_runtime_audit_summary_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    return result.returncode == 0


def load_gate_config() -> dict:
    if not GATE_CONFIG_PATH.exists():
        return {}

    return json.loads(GATE_CONFIG_PATH.read_text(encoding="utf-8"))


def pipeline_wiring_status() -> dict:
    text = PIPELINE_PATH.read_text(encoding="utf-8")

    risk_reject_pos = text.find("PIPE_RISK_REJECT")
    risk_router_pos = text.rfind("decision = self.risk_router.route(", 0, risk_reject_pos)
    gate_call_pos = text.rfind("if not self._check_session_side_execution_gate_v1(", 0, risk_router_pos)

    return {
        "has_gate_import": "SessionSideExecutionGateV1" in text,
        "has_audit_import": "SessionSideGateRuntimeAuditV1" in text,
        "has_gate_helper": "_check_session_side_execution_gate_v1" in text,
        "has_audit_ok_log": "PIPE_SESSION_SIDE_GATE_AUDIT_OK" in text,
        "has_gate_block_log": "PIPE_SESSION_SIDE_GATE_BLOCK" in text,
        "risk_reject_pos": risk_reject_pos,
        "risk_router_pos": risk_router_pos,
        "gate_call_pos": gate_call_pos,
        "order_ok": gate_call_pos != -1 and risk_router_pos != -1 and risk_reject_pos != -1 and gate_call_pos < risk_router_pos < risk_reject_pos,
    }


def main() -> int:
    database_url = os.getenv("DATABASE_URL") or build_psycopg_url()

    config = load_gate_config()
    allow_rows = len(config.get("allow", []) or [])
    block_rows = len(config.get("block", []) or [])
    insufficient_rows = len(config.get("insufficient_data", []) or [])

    wiring = pipeline_wiring_status()
    py_compile_ok = compile_ok()
    clean = git_clean()

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(AUDIT_SQL)
            audit = dict(cur.fetchone())

    status = "OK"

    if not clean:
        status = "WARN_GIT_DIRTY"
    elif not py_compile_ok:
        status = "FAIL_PY_COMPILE"
    elif allow_rows <= 0:
        status = "FAIL_NO_ALLOW_ROWS"
    elif block_rows <= 0:
        status = "FAIL_NO_BLOCK_ROWS"
    elif not wiring["order_ok"]:
        status = "FAIL_GATE_ORDER"
    elif int(audit["test_events"] or 0) > 0:
        status = "WARN_TEST_EVENTS"
    elif int(audit["raw_test_events"] or 0) > 0:
        status = "WARN_RAW_TEST_EVENTS"

    print("SESSION_SIDE_GATE_RUNTIME_FINAL_CHECK_V1", flush=True)

    print(
        "SESSION_SIDE_GATE_RUNTIME_FINAL_CHECK_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={py_compile_ok}",
        f"config_exists={GATE_CONFIG_PATH.exists()}",
        f"allow_rows={allow_rows}",
        f"block_rows={block_rows}",
        f"insufficient_rows={insufficient_rows}",
        f"audit_total_events={audit['total_events']}",
        f"audit_allowed_events={audit['allowed_events']}",
        f"audit_blocked_events={audit['blocked_events']}",
        f"audit_test_events={audit['test_events']}",
        f"audit_raw_test_events={audit['raw_test_events']}",
        f"audit_last_event_ts={audit['last_event_ts']}",
        flush=True,
    )

    print(
        "SESSION_SIDE_GATE_RUNTIME_FINAL_CHECK_WIRING",
        f"has_gate_import={wiring['has_gate_import']}",
        f"has_audit_import={wiring['has_audit_import']}",
        f"has_gate_helper={wiring['has_gate_helper']}",
        f"has_audit_ok_log={wiring['has_audit_ok_log']}",
        f"has_gate_block_log={wiring['has_gate_block_log']}",
        f"gate_call_pos={wiring['gate_call_pos']}",
        f"risk_router_pos={wiring['risk_router_pos']}",
        f"risk_reject_pos={wiring['risk_reject_pos']}",
        f"order_ok={wiring['order_ok']}",
        flush=True,
    )

    print(
        "SESSION_SIDE_GATE_RUNTIME_FINAL_CHECK_V1_OK",
        f"status={status}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
