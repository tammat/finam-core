from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Protocol

import psycopg2
import psycopg2.extras

from marketcore.action.contract_v2 import ActionIntentV2, InteractionKindV2
from marketcore.action.dispatcher_v2 import ActionAuditEventV2, AuditStageV2, DispatchStatusV2
from marketcore.action.postgres_adapters_v2 import PostgresActionAuditTrailV2


ROOT = Path("/opt/finam-core")


@dataclass(frozen=True, slots=True)
class WorkerCommandV2:
    request_kind: str
    argv: tuple[str, ...]
    expected_markers: tuple[str, ...]
    timeout_seconds: int


COMMANDS = {
    "EDGE_SEARCH_RUN": WorkerCommandV2(
        "EDGE_SEARCH_RUN", (str(ROOT / "venv/bin/python"), "src/scripts/run_autonomous_edge_search_cycle_v1.py"),
        ("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK", "live_allowed=0"), 1800,
    ),
    "RESEARCH_REFRESH": WorkerCommandV2(
        "RESEARCH_REFRESH", (str(ROOT / "venv/bin/python"), "src/scripts/run_market_universe_research_queue_cycle_v1.py"),
        ("VERDICT=MARKET_UNIVERSE_RESEARCH_QUEUE_CYCLE_V1_READY", "orders_changed=0", "fills_changed=0"), 1800,
    ),
    "PAPER_OBSERVATION": WorkerCommandV2(
        "PAPER_OBSERVATION", (str(ROOT / ".venv/bin/python"), "src/scripts/research/run_moex_session_paper_observation_v1.py"),
        ("TEST_MOEX_SESSION_PAPER_OBSERVATION_V1_OK", "orders_create=0", "execution_intents_create=0"), 1800,
    ),
}


class CommandExecutorV2(Protocol):
    def execute(self, command: WorkerCommandV2) -> str: ...


class SafeSubprocessCommandExecutorV2:
    def execute(self, command: WorkerCommandV2) -> str:
        env = os.environ.copy()
        env.update({
            "PYTHONPATH": str(ROOT / "src"),
            "DATABASE_URL": "postgresql:///finam_core",
            "RUNTIME_ALLOW_TRADING": "0",
            "EXECUTION_ENABLED": "0",
            "REAL_TRADING_ENABLED": "0",
        })
        if command.request_kind == "EDGE_SEARCH_RUN":
            env["EDGE_SEARCH_FORCE"] = "1"
        result = subprocess.run(command.argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=command.timeout_seconds, check=False)
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0:
            raise RuntimeError(f"WORKER_COMMAND_FAILED:{command.request_kind}:{result.returncode}")
        missing = [marker for marker in command.expected_markers if marker not in output]
        if missing:
            raise RuntimeError(f"WORKER_VERDICT_MISSING:{command.request_kind}:{','.join(missing)}")
        return next(
            (marker for marker in command.expected_markers if marker.startswith(("VERDICT=", "TEST_"))),
            "VERDICT=SAFE_COMMAND_COMPLETE",
        )


class GovernedCommandWorkerV2:
    def __init__(self, executor: CommandExecutorV2 | None = None) -> None:
        self._executor = executor or SafeSubprocessCommandExecutorV2()
        self._audit = PostgresActionAuditTrailV2()

    def run_once(self, *, request_id: str | None = None, request_kind: str | None = None) -> str | None:
        if request_kind is not None and request_kind not in COMMANDS:
            raise ValueError("WORKER_REQUEST_KIND_FORBIDDEN")
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT request_id,action_id,request_kind,command_code,actor_id,target_id
                    FROM marketcore_action.command_request_v2
                    WHERE status='PENDING'
                      AND (%s IS NULL OR request_id=%s)
                      AND (%s IS NULL OR request_kind=%s)
                    ORDER BY requested_at
                    FOR UPDATE SKIP LOCKED LIMIT 1
                    """, (request_id, request_id, request_kind, request_kind),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute("UPDATE marketcore_action.command_request_v2 SET status='RUNNING',started_at=clock_timestamp() WHERE request_id=%s", (row["request_id"],))
        command = COMMANDS.get(str(row["request_kind"]))
        if row["request_kind"] == "OPERATOR_DECISION_ACKNOWLEDGE":
            return self._acknowledge_operator_decision(row)
        if row["request_kind"] == "OPERATOR_DECISION_MEASURE":
            return self._measure_operator_decision(row)
        if command is None:
            return self._finish(row, False, None, "WORKER_REQUEST_KIND_FORBIDDEN")
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        try:
            result = self._executor.execute(command)
        except Exception as exc:
            failure = str(exc).strip() or type(exc).__name__
            return self._finish(row, False, None, failure[:256])
        return self._finish(row, True, result, None)

    def _acknowledge_operator_decision(self, row) -> str:
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        try:
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE analytics.operator_decision_workspace_v2 d
                        SET selection_status='ACKNOWLEDGED',selected_at=clock_timestamp(),
                            selected_by=%s,
                            baseline_value=CASE d.action_code
                              WHEN 'REVIEW_SHADOW_LOSS' THEN (SELECT abs(coalesce(sum(net_pnl),0)) FROM analytics.profit_funnel_shadow_paper_admission_v2 WHERE admission_status='REJECTED' AND net_pnl<0)
                              WHEN 'REVIEW_FORWARD_ADMISSION' THEN (SELECT count(*) FROM analytics.profit_funnel_oos_forward_handoff_v2 WHERE handoff_status='ADMITTED')
                              WHEN 'RESTORE_RUNTIME_EVIDENCE' THEN (SELECT count(*) FROM analytics.profit_funnel_paper_runtime_admission_v2 WHERE admission_status='ADMITTED')
                              ELSE 0 END,
                            measurement_due_at=clock_timestamp()+interval '1 hour',
                            expires_at=clock_timestamp()+interval '2 hours',updated_at=clock_timestamp()
                        WHERE decision_id=%s::uuid AND policy_verdict='REVIEW_REQUIRED'
                          AND expires_at>clock_timestamp() AND selection_status='NOT_SELECTED'
                        RETURNING decision_id
                    """, (row["actor_id"],row["target_id"]))
                    selected = cursor.fetchone()
                    if selected is None:
                        raise ValueError("OPERATOR_DECISION_NOT_ACKNOWLEDGEABLE")
            return self._finish(row, True, f"acknowledged:{selected[0]}", None)
        except Exception as exc:
            return self._finish(row, False, None, str(exc)[:256])

    def _measure_operator_decision(self, row) -> str:
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        try:
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""
                        SELECT decision_id,action_code,baseline_value
                        FROM analytics.operator_decision_workspace_v2
                        WHERE decision_id=%s::uuid AND selection_status='ACKNOWLEDGED'
                          AND feedback_status='PENDING' AND measurement_due_at<=clock_timestamp()
                        FOR UPDATE
                    """, (row["target_id"],))
                    decision = cursor.fetchone()
                    if decision is None:
                        raise ValueError("OPERATOR_DECISION_NOT_MEASURABLE")
                    measurements = {
                        "REVIEW_SHADOW_LOSS": ("SELECT abs(coalesce(sum(net_pnl),0)) AS current_value FROM analytics.profit_funnel_shadow_paper_admission_v2 WHERE admission_status='REJECTED' AND net_pnl<0", "analytics.profit_funnel_shadow_paper_admission_v2"),
                        "REVIEW_FORWARD_ADMISSION": ("SELECT count(*) AS current_value FROM analytics.profit_funnel_oos_forward_handoff_v2 WHERE handoff_status='ADMITTED'", "analytics.profit_funnel_oos_forward_handoff_v2"),
                        "RESTORE_RUNTIME_EVIDENCE": ("SELECT count(*) AS current_value FROM analytics.profit_funnel_paper_runtime_admission_v2 WHERE admission_status='ADMITTED'", "analytics.profit_funnel_paper_runtime_admission_v2"),
                    }
                    measurement = measurements.get(decision["action_code"])
                    if measurement is None:
                        raise ValueError("OPERATOR_DECISION_MEASUREMENT_SOURCE_FORBIDDEN")
                    query, source_identity = measurement
                    cursor.execute(query)
                    current_value = cursor.fetchone()["current_value"]
                    baseline = decision["baseline_value"]
                    actual_result = baseline-current_value if decision["action_code"] == "REVIEW_SHADOW_LOSS" else current_value-baseline
                    cursor.execute("""
                        UPDATE analytics.operator_decision_workspace_v2
                        SET actual_result=%s,feedback_status='MEASURED',measured_at=clock_timestamp(),
                            measurement_source_identity=%s,updated_at=clock_timestamp()
                        WHERE decision_id=%s RETURNING decision_id
                    """, (actual_result,source_identity,decision["decision_id"]))
                    measured = cursor.fetchone()["decision_id"]
            return self._finish(row, True, f"measured:{measured}", None)
        except Exception as exc:
            return self._finish(row, False, None, str(exc)[:256])

    def _finish(self, row, success: bool, result: str | None, failure: str | None) -> str:
        status = "COMPLETED" if success else "FAILED"
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE marketcore_action.command_request_v2 SET status=%s,finished_at=clock_timestamp(),result_reference=%s,failure_code=%s WHERE request_id=%s AND status='RUNNING'",
                    (status, result, failure, row["request_id"]),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("WORKER_REQUEST_STATE_CONFLICT")
        self._record(row, AuditStageV2.EXECUTION_FINISHED, DispatchStatusV2.EXECUTED if success else DispatchStatusV2.FAILED, "WORKER_COMPLETED" if success else "WORKER_FAILED", result)
        return status

    def _record(self, row, stage, status, reason, result=None) -> None:
        self._audit.append(ActionAuditEventV2(
            occurred_at=datetime.now(timezone.utc), stage=stage,
            action_id=row["action_id"], actor_id=row["actor_id"],
            interaction_kind=InteractionKindV2.DOUBLE_CLICK.value,
            status=status, reason_code=reason, target_id=None,
            command_code=row["command_code"], policy_class=None,
            risk_guard_code=None, idempotency_key=row["request_id"],
            approval_granted=False, result_reference=result,
        ))


class PostgresPendingRequestRollbackHandlerV2:
    def rollback(self, intent: ActionIntentV2, rollback_code: str, result_reference: str) -> str:
        expected = {"RESEARCH.CANCEL_PENDING_REQUEST", "PAPER.CANCEL_PENDING_REQUEST", "OPERATOR.CANCEL_PENDING_ACKNOWLEDGEMENT", "OPERATOR.CANCEL_PENDING_MEASUREMENT"}
        if rollback_code not in expected:
            raise ValueError("PENDING_REQUEST_ROLLBACK_FORBIDDEN")
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE marketcore_action.command_request_v2 SET status='CANCELLED',finished_at=clock_timestamp(),result_reference=%s WHERE request_id=%s AND action_id=%s AND status='PENDING' RETURNING request_id",
                    (f"rollback:{result_reference}", result_reference, intent.action_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("PENDING_REQUEST_NOT_ROLLBACKABLE")
        return f"cancelled:{row[0]}"
