from __future__ import annotations

import os
import uuid
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
        ("VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK", "live_allowed=0"), 10800,
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
        argv = command.argv
        if command.request_kind == "EDGE_SEARCH_RUN":
            # Research is intentionally best-effort: market data, accounting and
            # safety processes always keep precedence on the shared server.
            argv = ("nice", "-n", "10", "ionice", "-c", "2", "-n", "7", *argv)
        result = subprocess.run(argv, cwd=ROOT, env=env, text=True, capture_output=True, timeout=command.timeout_seconds, check=False)
        output = f"{result.stdout}\n{result.stderr}"
        if result.returncode != 0:
            raise RuntimeError(f"WORKER_COMMAND_FAILED:{command.request_kind}:{result.returncode}")
        if command.request_kind == "EDGE_SEARCH_RUN":
            verdicts = (
                "VERDICT=AUTONOMOUS_EDGE_SEARCH_CYCLE_V1_OK",
                "VERDICT=AUTONOMOUS_EDGE_SEARCH_RESOURCE_GUARD_OK",
                "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED",
            )
            missing = ["live_allowed=0"] if "live_allowed=0" not in output else []
            if not any(verdict in output for verdict in verdicts):
                missing.append("EDGE_SEARCH_TERMINAL_VERDICT")
            if missing:
                raise RuntimeError(f"WORKER_VERDICT_MISSING:{command.request_kind}:{','.join(missing)}")
            return next(verdict for verdict in verdicts if verdict in output)
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
        inline_commands = {"OPERATOR_DECISION_ACKNOWLEDGE", "OPERATOR_DECISION_MEASURE", "OPERATOR_DECISION_REFRESH", "EDGE_SEARCH_CANCEL",
                           "RESEARCH_UNIVERSE_INCLUDE", "RESEARCH_UNIVERSE_EXCLUDE", "RESEARCH_UNIVERSE_PRIORITY",
                           "ENTRY_EXIT_CONFIRM_PAPER", "ENTRY_EXIT_REJECT", "ENTRY_EXIT_CONTINUE_SHADOW", "ENTRY_EXIT_ROLLBACK"}
        if request_kind is not None and request_kind not in COMMANDS and request_kind not in inline_commands:
            raise ValueError("WORKER_REQUEST_KIND_FORBIDDEN")
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                cursor.execute(
                    """
                    SELECT q.request_id,q.action_id,q.request_kind,q.command_code,q.actor_id,q.target_id,q.process_id,p.variant_budget AS edge_search_variant_budget,p.cycle_budget AS edge_search_cycle_budget
                    FROM marketcore_action.command_request_v2 q
LEFT JOIN marketcore_action.edge_search_request_parameter_v1 p
  ON p.request_id=q.request_id
                    WHERE status='PENDING'
                      AND (%s IS NULL OR q.request_id=%s)
                      AND (%s IS NULL OR q.request_kind=%s)
                    ORDER BY priority,requested_at
                    FOR UPDATE OF q SKIP LOCKED LIMIT 1
                    """, (request_id, request_id, request_kind, request_kind),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute("UPDATE marketcore_action.command_request_v2 SET status='RUNNING',started_at=clock_timestamp() WHERE request_id=%s", (row["request_id"],))
                if row["process_id"] is not None:
                    cursor.execute("""UPDATE marketcore_action.research_process_v1
                        SET status_code='RUNNING',progress_pct=5,current_step_code='STARTING',
                            started_at=clock_timestamp(),finished_at=NULL,updated_at=clock_timestamp()
                        WHERE process_id=%s""", (row["process_id"],))
                    cursor.execute("""INSERT INTO marketcore_action.research_process_event_v1
                        (process_id,event_code,status_code,progress_pct,step_code,payload)
                        VALUES(%s,'EXECUTION_STARTED','RUNNING',5,'STARTING',
                               jsonb_build_object('request_id',%s))""",
                        (row["process_id"],row["request_id"]))
        command = COMMANDS.get(str(row["request_kind"]))
        if row["request_kind"] == "OPERATOR_DECISION_ACKNOWLEDGE":
            return self._acknowledge_operator_decision(row)
        if row["request_kind"] == "OPERATOR_DECISION_MEASURE":
            return self._measure_operator_decision(row)
        if row["request_kind"] == "OPERATOR_DECISION_REFRESH":
            return self._refresh_operator_decision(row)
        if row["request_kind"] == "EDGE_SEARCH_CANCEL":
            return self._cancel_edge_search(row)
        if str(row["request_kind"]).startswith("RESEARCH_UNIVERSE_"):
            return self._apply_universe_override(row)
        if str(row["request_kind"]).startswith("ENTRY_EXIT_"):
            return self._apply_entry_exit_decision(row)
        if command is None:
            return self._finish(row, False, None, "WORKER_REQUEST_KIND_FORBIDDEN")
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        try:
            if row["request_kind"] == "EDGE_SEARCH_RUN":
                os.environ["EDGE_SEARCH_REQUEST_ID"] = str(row["request_id"])
                # Scheduled research must obey the server resource guard. Only
                # an explicit operator request may override the low-load window.
                os.environ["EDGE_SEARCH_FORCE"] = (
                    "0" if row["actor_id"] == "system.scheduler" else "1"
                )

                raw_target = str(row["target_id"] or "").strip()
                if raw_target.startswith("TARGETED_V1|"):
                    parts = [part.strip() for part in raw_target.split("|")]

                    if len(parts) != 5:
                        raise ValueError(
                            "TARGETED_EDGE_SEARCH_TARGET_INVALID_PART_COUNT"
                        )

                    _, research_family, symbol, strategy, side = parts
                    side = side.upper()

                    if research_family not in {"EXIT_OOS", "ECONOMIC_OOS"}:
                        raise ValueError(
                            "TARGETED_EDGE_SEARCH_FAMILY_INVALID"
                        )

                    if not symbol or "@" not in symbol:
                        raise ValueError(
                            "TARGETED_EDGE_SEARCH_PHYSICAL_SYMBOL_REQUIRED"
                        )

                    if not strategy:
                        raise ValueError(
                            "TARGETED_EDGE_SEARCH_STRATEGY_REQUIRED"
                        )

                    if side not in {"LONG", "SHORT"}:
                        raise ValueError(
                            "TARGETED_EDGE_SEARCH_SIDE_INVALID"
                        )

                    os.environ["EDGE_SEARCH_TARGET_MODE"] = "TARGETED_V1"
                    os.environ[
                        "EDGE_SEARCH_TARGET_RESEARCH_FAMILY"
                    ] = research_family
                    os.environ["EDGE_SEARCH_TARGET_SYMBOL"] = symbol
                    os.environ["EDGE_SEARCH_TARGET_STRATEGY"] = strategy
                    os.environ["EDGE_SEARCH_TARGET_SIDE"] = side
                    variant_budget = row.get("edge_search_variant_budget")
                    cycle_budget = row.get("edge_search_cycle_budget")
                    if variant_budget is not None:
                        variant_budget = int(variant_budget)

                        if variant_budget <= 0:
                            raise RuntimeError(
                                "EDGE_SEARCH_TARGET_VARIANT_BUDGET_INVALID"
                            )

                        os.environ["EDGE_SEARCH_TARGET_VARIANT_BUDGET"] = (
                            str(variant_budget)
                        )

                        resolved_cycle_budget = (
                            int(cycle_budget)
                            if cycle_budget is not None
                            else 1
                        )

                        if resolved_cycle_budget <= 0:
                            raise RuntimeError(
                                "EDGE_SEARCH_TARGET_CYCLE_BUDGET_INVALID"
                            )

                        if resolved_cycle_budget > variant_budget:
                            raise RuntimeError(
                                "EDGE_SEARCH_TARGET_CYCLE_BUDGET_EXCEEDS_VARIANT_BUDGET"
                            )

                        os.environ["EDGE_SEARCH_TARGET_CYCLE_BUDGET"] = (
                            str(resolved_cycle_budget)
                        )
            if row["process_id"] is not None:
                os.environ["MARKETCORE_PROCESS_ID"] = str(row["process_id"])
            result = self._executor.execute(command)
        except Exception as exc:
            failure = str(exc).strip() or type(exc).__name__
            return self._finish(row, False, None, failure[:256])
        finally:
            if row["request_kind"] == "EDGE_SEARCH_RUN":
                os.environ.pop("EDGE_SEARCH_REQUEST_ID", None)
                os.environ.pop("EDGE_SEARCH_FORCE", None)
                os.environ.pop("EDGE_SEARCH_TARGET_MODE", None)
                os.environ.pop("EDGE_SEARCH_TARGET_RESEARCH_FAMILY", None)
                os.environ.pop("EDGE_SEARCH_TARGET_SYMBOL", None)
                os.environ.pop("EDGE_SEARCH_TARGET_STRATEGY", None)
                os.environ.pop("EDGE_SEARCH_TARGET_SIDE", None)
                os.environ.pop(
                    "EDGE_SEARCH_TARGET_VARIANT_BUDGET", None
                )
                os.environ.pop(
                    "EDGE_SEARCH_TARGET_CYCLE_BUDGET", None
                )
            os.environ.pop("MARKETCORE_PROCESS_ID", None)
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

    def _cancel_edge_search(self, row) -> str:
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute("""UPDATE marketcore_action.command_request_v2 SET status='CANCELLED',
                    finished_at=clock_timestamp(),result_reference=%s
                    WHERE request_id=(SELECT request_id FROM marketcore_action.command_request_v2
                      WHERE request_kind='EDGE_SEARCH_RUN' AND status='PENDING'
                        AND actor_id=%s AND actor_id<>'system.scheduler'
                      ORDER BY requested_at DESC LIMIT 1) RETURNING request_id""",
                    (f"cancelled_by:{row['request_id']}", row["actor_id"]))
                cancelled=cursor.fetchone()
        if cancelled is None:
            return self._finish(row,False,None,"EDGE_SEARCH_PENDING_REQUEST_NOT_FOUND")
        return self._finish(row,True,f"cancelled:{cancelled[0]}",None)

    def _refresh_operator_decision(self, row) -> str:
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        try:
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor() as cursor:
                    cursor.execute("""
                        UPDATE analytics.operator_decision_workspace_v2
                        SET selection_status='NOT_SELECTED',selected_at=NULL,selected_by=NULL,
                            baseline_value=NULL,measurement_due_at=NULL,measured_at=NULL,
                            measurement_source_identity=NULL,actual_result=NULL,
                            feedback_status='PENDING',expires_at=clock_timestamp()+interval '2 hours',
                            updated_at=clock_timestamp()
                        WHERE decision_id=%s::uuid AND policy_verdict='REVIEW_REQUIRED'
                          AND feedback_status='MEASURED'
                        RETURNING decision_id
                    """, (row["target_id"],))
                    refreshed = cursor.fetchone()
                    if refreshed is None:
                        raise ValueError("OPERATOR_DECISION_NOT_REFRESHABLE")
            return self._finish(row, True, f"refreshed:{refreshed[0]}", None)
        except Exception as exc:
            return self._finish(row, False, None, str(exc)[:256])

    def _apply_universe_override(self, row) -> str:
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        raw_target = str(row["target_id"] or "")
        symbol, _, priority_text = raw_target.partition("|")
        symbol = symbol.strip().upper()
        if not symbol or len(symbol) > 64:
            return self._finish(row, False, None, "RESEARCH_UNIVERSE_SYMBOL_INVALID")
        try:
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor() as cursor:
                    if row["request_kind"] == "RESEARCH_UNIVERSE_PRIORITY":
                        priority = int(priority_text)
                        if priority < 1 or priority > 100:
                            raise ValueError("RESEARCH_UNIVERSE_PRIORITY_INVALID")
                        cursor.execute("SELECT priority_override FROM analytics.edge_research_universe_override_v1 WHERE symbol=%s AND active", (symbol,))
                        existing = cursor.fetchone()
                        if existing is not None and existing[0] == priority:
                            return self._finish(row, True, f"unchanged:priority:{symbol}:{priority}", None)
                        cursor.execute("""INSERT INTO analytics.edge_research_universe_override_v1
                            (symbol,priority_override,request_id,requested_by) VALUES(%s,%s,%s::uuid,%s)
                            ON CONFLICT(symbol) DO UPDATE SET priority_override=excluded.priority_override,
                              request_id=excluded.request_id,requested_by=excluded.requested_by,
                              active=true,updated_at=clock_timestamp()""",
                            (symbol,priority,row["request_id"],row["actor_id"]))
                        result = f"priority:{symbol}:{priority}"
                    else:
                        mode = "FORCE_INCLUDE" if row["request_kind"] == "RESEARCH_UNIVERSE_INCLUDE" else "FORCE_EXCLUDE"
                        cursor.execute("SELECT inclusion_mode FROM analytics.edge_research_universe_override_v1 WHERE symbol=%s AND active", (symbol,))
                        existing = cursor.fetchone()
                        if existing is not None and existing[0] == mode:
                            return self._finish(row, True, f"unchanged:{mode.lower()}:{symbol}", None)
                        cursor.execute("""INSERT INTO analytics.edge_research_universe_override_v1
                            (symbol,inclusion_mode,request_id,requested_by) VALUES(%s,%s,%s::uuid,%s)
                            ON CONFLICT(symbol) DO UPDATE SET inclusion_mode=excluded.inclusion_mode,
                              request_id=excluded.request_id,requested_by=excluded.requested_by,
                              active=true,updated_at=clock_timestamp()""",
                            (symbol,mode,row["request_id"],row["actor_id"]))
                        result = f"{mode.lower()}:{symbol}"
            return self._finish(row, True, result, None)
        except Exception as exc:
            return self._finish(row, False, None, str(exc)[:256])

    def _apply_entry_exit_decision(self, row) -> str:
        self._record(row, AuditStageV2.EXECUTION_STARTED, DispatchStatusV2.EXECUTED, "WORKER_STARTED")
        parts = str(row["target_id"] or "").split("|", 3)
        if len(parts) != 4 or any(not part.strip() for part in parts):
            return self._finish(row, False, None, "ENTRY_EXIT_TARGET_INVALID")
        strategy, group, side, candidate = (part.strip() for part in parts)
        try:
            with psycopg2.connect("postgresql:///finam_core") as connection:
                with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute("""SELECT * FROM analytics.entry_exit_recommendation_v1
                        WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s AND candidate_code=%s
                        FOR UPDATE""", (strategy,group,side,candidate))
                    recommendation = cursor.fetchone()
                    if recommendation is None:
                        raise ValueError("ENTRY_EXIT_RECOMMENDATION_NOT_FOUND")
                    kind = str(row["request_kind"])
                    decision = kind.removeprefix("ENTRY_EXIT_")
                    reason = "OPERATOR_SELECTED"
                    if kind == "ENTRY_EXIT_CONFIRM_PAPER":
                        cursor.execute("""SELECT challenger_status,challenger_candidate_code
                            FROM analytics.entry_exit_champion_challenger_v1
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s FOR UPDATE""",
                            (strategy,group,side))
                        challenger = cursor.fetchone()
                        if (challenger is None
                                or challenger["challenger_status"] != "READY_FOR_CHAMPION_CONFIRMATION"
                                or challenger["challenger_candidate_code"] != candidate):
                            raise ValueError("ENTRY_EXIT_GUARDS_NOT_PASSED")
                        runtime_supported = (
                            group in {"GAZP", "LKOH", "NVTK", "SBER", "SBERP", "VTBR"}
                            and recommendation["entry_mode"] in {"IMMEDIATE", "ADAPTIVE"}
                        )
                        if not runtime_supported:
                            raise ValueError("ENTRY_EXIT_MODE_NOT_RUNTIME_SUPPORTED")
                        cursor.execute("""UPDATE analytics.entry_exit_runtime_profile_v1
                            SET status='SUPERSEDED',deactivated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                              AND execution_mode='paper' AND status='ACTIVE'""", (strategy,group,side))
                        cursor.execute("""INSERT INTO analytics.entry_exit_runtime_profile_v1
                            (strategy_code,symbol_group,side_code,candidate_code,status,entry_mode,stop_atr,take_atr,
                             trail_after_r,trail_atr,source_metrics,activated_by)
                            VALUES(%s,%s,%s,%s,'ACTIVE',%s,%s,%s,%s,%s,%s,%s) RETURNING profile_id""",
                            (strategy,group,side,candidate,recommendation["entry_mode"],recommendation["stop_atr"],
                             recommendation["take_atr"],recommendation["trail_after_r"],recommendation["trail_atr"],
                             psycopg2.extras.Json(recommendation["metrics"]),row["actor_id"]))
                        reason = f"PAPER_PROFILE_ACTIVE:{cursor.fetchone()['profile_id']}"
                        cursor.execute("""UPDATE analytics.entry_exit_champion_challenger_v1
                            SET challenger_status='CHAMPION_ACTIVE',champion_candidate_code=%s,
                                champion_profile_id=(SELECT profile_id FROM analytics.entry_exit_runtime_profile_v1
                                  WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                                    AND execution_mode='paper' AND status='ACTIVE'),
                                updated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s""",
                            (candidate,strategy,group,side,strategy,group,side))
                    elif kind == "ENTRY_EXIT_ROLLBACK":
                        cursor.execute("""UPDATE analytics.entry_exit_runtime_profile_v1
                            SET status='ROLLED_BACK',deactivated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s AND candidate_code=%s
                              AND execution_mode='paper' AND status='ACTIVE' RETURNING profile_id""",
                            (strategy,group,side,candidate))
                        active = cursor.fetchone()
                        if active is None:
                            raise ValueError("ENTRY_EXIT_ACTIVE_PROFILE_NOT_FOUND")
                        cursor.execute("""UPDATE analytics.entry_exit_runtime_profile_v1 SET status='ACTIVE',deactivated_at=NULL
                            WHERE profile_id=(SELECT profile_id FROM analytics.entry_exit_runtime_profile_v1
                              WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s AND execution_mode='paper'
                                AND status='SUPERSEDED' ORDER BY deactivated_at DESC LIMIT 1)
                            RETURNING profile_id,candidate_code""", (strategy,group,side))
                        previous = cursor.fetchone()
                        reason = f"ROLLED_BACK:{active['profile_id']}:RESTORED:{previous['profile_id'] if previous else 'BASELINE'}"
                        cursor.execute("""UPDATE analytics.entry_exit_champion_challenger_v1
                            SET challenger_status='ROLLED_BACK',
                                champion_candidate_code=coalesce(%s,'CURRENT_PAPER'),
                                champion_profile_id=%s,updated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s""",
                            ((previous or {}).get("candidate_code"), (previous or {}).get("profile_id"),
                             strategy,group,side))
                    elif kind == "ENTRY_EXIT_REJECT":
                        if recommendation.get("operator_decision") == "CONFIRM_PAPER":
                            raise ValueError("ENTRY_EXIT_ACTIVE_PROFILE_MUST_ROLLBACK")
                        cursor.execute("""UPDATE analytics.entry_exit_champion_challenger_v1
                            SET challenger_status='REJECTED',updated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                              AND challenger_candidate_code=%s""", (strategy,group,side,candidate))
                    elif kind == "ENTRY_EXIT_CONTINUE_SHADOW":
                        cursor.execute("""UPDATE analytics.entry_exit_champion_challenger_v1
                            SET challenger_status='SHADOW_ACCUMULATION',challenger_selected_at=NULL,
                                paper_metrics='{}'::jsonb,updated_at=clock_timestamp()
                            WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s
                              AND challenger_candidate_code=%s""", (strategy,group,side,candidate))
                    else:
                        raise ValueError("ENTRY_EXIT_DECISION_FORBIDDEN")
                    cursor.execute("""UPDATE analytics.entry_exit_recommendation_v1
                        SET operator_decision=%s,operator_decided_at=clock_timestamp()
                        WHERE strategy_code=%s AND symbol_group=%s AND side_code=%s AND candidate_code=%s""",
                        (decision,strategy,group,side,candidate))
                    cursor.execute("""INSERT INTO analytics.entry_exit_operator_decision_v1
                        (strategy_code,symbol_group,side_code,candidate_code,decision_code,actor_id,request_id,reason_code)
                        VALUES(%s,%s,%s,%s,%s,%s,%s::uuid,%s)""",
                        (strategy,group,side,candidate,decision,row["actor_id"],row["request_id"],reason))
            return self._finish(row, True, f"{decision.lower()}:{strategy}:{group}:{side}:{candidate}", None)
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
        continuation_required = (
            success
            and row["request_kind"] == "EDGE_SEARCH_RUN"
            and result == "VERDICT=AUTONOMOUS_EDGE_SEARCH_CHECKPOINTED"
        )
        status = "COMPLETED" if success else "FAILED"

        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "UPDATE marketcore_action.command_request_v2 SET status=%s,finished_at=clock_timestamp(),result_reference=%s,failure_code=%s WHERE request_id=%s AND status='RUNNING'",
                    (status, result, failure, row["request_id"]),
                )
                if cursor.rowcount != 1:
                    raise RuntimeError("WORKER_REQUEST_STATE_CONFLICT")

                if continuation_required:
                    continuation_id = str(
                        uuid.uuid5(
                            uuid.UUID(str(row["request_id"])),
                            "EDGE_SEARCH_CHECKPOINT_CONTINUATION_V1",
                        )
                    )
                    cursor.execute(
                        """
                        INSERT INTO marketcore_action.command_request_v2
                          (request_id,action_id,request_kind,command_code,actor_id,
                           target_id,status,requested_at)
                        VALUES
                          (%s,%s,'EDGE_SEARCH_RUN',%s,%s,%s,'PENDING',
                           clock_timestamp())
                        ON CONFLICT(request_id) DO NOTHING
                        """,
                        (
                            continuation_id,
                            row["action_id"],
                            row["command_code"],
                            row["actor_id"],
                            row["target_id"],
                        ),
                    )

                if row.get("process_id") is not None and not continuation_required:
                    process_status = "SUCCEEDED" if success else "FAILED"
                    cursor.execute("""UPDATE marketcore_action.research_process_v1
                        SET status_code=%s,progress_pct=100,current_step_code='COMPLETE',
                            outcome_code=coalesce(outcome_code,%s),reason_code=coalesce(reason_code,%s),
                            recommendation_code=CASE
                                WHEN %s AND recommendation_code='WAIT_FOR_SYSTEM_ANALYSIS'
                                THEN 'NO_ACTION_REQUIRED'
                                ELSE recommendation_code END,
                            explanation_ru=coalesce(explanation_ru,%s),finished_at=clock_timestamp(),
                            updated_at=clock_timestamp()
                        WHERE process_id=%s""",
                        (process_status,"COMPLETED" if success else "FAILED",failure,success,
                         "Процесс завершён" if success else "Процесс завершился с ошибкой",
                         row["process_id"]))
                    cursor.execute("""INSERT INTO marketcore_action.research_process_event_v1
                        (process_id,event_code,status_code,progress_pct,step_code,payload)
                        VALUES(%s,'EXECUTION_FINISHED',%s,100,'COMPLETE',
                               jsonb_build_object('request_id',%s,'result',%s,'failure',%s))""",
                        (row["process_id"],process_status,row["request_id"],result,failure))

        self._record(
            row,
            AuditStageV2.EXECUTION_FINISHED,
            DispatchStatusV2.EXECUTED if success else DispatchStatusV2.FAILED,
            "WORKER_RESUMABLE" if continuation_required
            else ("WORKER_COMPLETED" if success else "WORKER_FAILED"),
            result,
        )
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
