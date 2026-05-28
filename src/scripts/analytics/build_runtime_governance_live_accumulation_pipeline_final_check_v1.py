from __future__ import annotations

import subprocess
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.execution.runtime_governance_live_accumulation_v1 import (
    RuntimeGovernanceLiveAccumulatorV1,
    RuntimeGovernanceLiveDecisionV1,
)


PIPELINE_PATH = Path("src/finam_core/pipelines/paper_pipeline.py")
TEST_SOURCE = "runtime_governance_live_accumulation_pipeline_final_check_v1"


DELETE_SQL = """
DELETE FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s;
"""


SUMMARY_SQL = """
SELECT
    count(*) AS rows_written,
    count(*) FILTER (WHERE allowed = true) AS allowed_rows,
    count(*) FILTER (WHERE allowed = false) AS blocked_rows,
    count(*) FILTER (WHERE action = 'FAILED_OPEN') AS failed_open_rows,
    max(created_at) AS last_event_ts
FROM runtime_governance_live_accumulation_v1
WHERE raw_json->>'source' = %(source)s;
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
            "src/finam_core/execution/runtime_governance_live_accumulation_v1.py",
            "src/finam_core/pipelines/paper_pipeline.py",
            "src/scripts/analytics/build_runtime_governance_live_accumulation_pipeline_final_check_v1.py",
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="")

    return result.returncode == 0


def wiring_ok() -> bool:
    pipeline = PIPELINE_PATH.read_text(encoding="utf-8")

    required = [
        "RuntimeGovernanceLiveAccumulatorV1",
        "RuntimeGovernanceLiveDecisionV1",
        "self.runtime_governance_live_accumulator_v1",
        "def _record_runtime_governance_live_accumulation_v1(",
        "PIPE_RUNTIME_EDGE_GOVERNANCE_LIVE_ACCUMULATION_FAILED_OPEN",
        "paper_pipeline_phase2_runtime",
        "runtime_governance_live_accumulation_v1_call",
    ]

    missing = [x for x in required if x not in pipeline]

    phase2_pos = pipeline.find("PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_DECISION")
    call_pos = pipeline.find("runtime_governance_live_accumulation_v1_call")
    soft_block_pos = pipeline.find("PIPE_RUNTIME_EDGE_GOVERNANCE_PHASE2_SOFT_BLOCK")

    order_ok = (
        phase2_pos != -1
        and call_pos != -1
        and soft_block_pos != -1
        and phase2_pos < call_pos < soft_block_pos
    )

    if missing:
        print(f"LIVE_ACCUMULATION_WIRING_MISSING missing={missing}", flush=True)

    if not order_ok:
        print(
            "LIVE_ACCUMULATION_WIRING_ORDER_BAD",
            f"phase2_pos={phase2_pos}",
            f"call_pos={call_pos}",
            f"soft_block_pos={soft_block_pos}",
            flush=True,
        )

    return not missing and order_ok


def postgres_write_ok() -> tuple[bool, dict]:
    accumulator = RuntimeGovernanceLiveAccumulatorV1()
    accumulator.ensure_schema()

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(DELETE_SQL, {"source": TEST_SOURCE})
        conn.commit()

    accumulator.append(
        RuntimeGovernanceLiveDecisionV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=10,
            allowed=True,
            action="ALLOW",
            reason="runtime_edge_governance_allow",
            session_action="ALLOW",
            strict_reason="strict_mode_positive_expectancy",
            decay_state="HEALTHY",
            expectancy_points=0.0533,
            closed_trades=123,
            raw_json={"source": TEST_SOURCE, "check": "allow"},
        )
    )

    accumulator.append(
        RuntimeGovernanceLiveDecisionV1(
            symbol="BR_ROLLING@RTSX",
            side="BUY",
            hour_msk=19,
            allowed=False,
            action="SOFT_BLOCK",
            reason="session_side_gate_block",
            session_action="BLOCK",
            strict_reason=None,
            decay_state="DECAY",
            expectancy_points=-0.0486,
            closed_trades=86,
            raw_json={"source": TEST_SOURCE, "check": "soft_block"},
        )
    )

    with psycopg.connect(build_psycopg_url(), row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            cur.execute(SUMMARY_SQL, {"source": TEST_SOURCE})
            row = dict(cur.fetchone())

    ok = (
        int(row["rows_written"] or 0) == 2
        and int(row["allowed_rows"] or 0) == 1
        and int(row["blocked_rows"] or 0) == 1
        and int(row["failed_open_rows"] or 0) == 0
    )

    return ok, row


def main() -> int:
    compile_status = py_compile_ok()
    wiring_status = wiring_ok()
    write_status, row = postgres_write_ok()

    clean = git_clean()

    ready = (
        compile_status
        and wiring_status
        and write_status
        and clean
    )

    status = (
        "LIVE_ACCUMULATION_PIPELINE_READY"
        if ready
        else "WARN_GIT_DIRTY" if not clean
        else "LIVE_ACCUMULATION_PIPELINE_NOT_READY"
    )

    print("RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_PIPELINE_FINAL_CHECK_V1")
    print(
        "RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_PIPELINE_FINAL_STATUS",
        f"status={status}",
        f"git_clean={clean}",
        f"py_compile_ok={compile_status}",
        f"wiring_ok={wiring_status}",
        f"postgres_write_ok={write_status}",
        f"rows_written={row['rows_written']}",
        f"allowed_rows={row['allowed_rows']}",
        f"blocked_rows={row['blocked_rows']}",
        f"failed_open_rows={row['failed_open_rows']}",
        f"last_event_ts={row['last_event_ts']}",
        flush=True,
    )
    print(
        f"RUNTIME_GOVERNANCE_LIVE_ACCUMULATION_PIPELINE_FINAL_CHECK_V1_OK status={status}",
        flush=True,
    )

    return 0 if compile_status and wiring_status and write_status else 1


if __name__ == "__main__":
    raise SystemExit(main())
