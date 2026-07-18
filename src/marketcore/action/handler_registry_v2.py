from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping
from uuid import UUID

import psycopg2

from marketcore.action.contract_v2 import ActionIntentV2


@dataclass(frozen=True, slots=True)
class StateChangingActionDefinitionV2:
    action_id: str
    command_code: str
    policy_class: str
    authorization_scope: str
    rollback_code: str
    request_kind: str


_DEFINITIONS: Mapping[str, StateChangingActionDefinitionV2] = MappingProxyType({
    "research.request.refresh": StateChangingActionDefinitionV2(
        "research.request.refresh", "RESEARCH.REQUEST_REFRESH", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.CANCEL_PENDING_REQUEST", "RESEARCH_REFRESH",
    ),
    "research.edge_search.run": StateChangingActionDefinitionV2(
        "research.edge_search.run", "RESEARCH.RUN_EDGE_SEARCH", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.CANCEL_PENDING_REQUEST", "EDGE_SEARCH_RUN",
    ),
    "research.edge_search.cancel": StateChangingActionDefinitionV2(
        "research.edge_search.cancel", "RESEARCH.CANCEL_EDGE_SEARCH", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.CANCEL_PENDING_REQUEST", "EDGE_SEARCH_CANCEL",
    ),
    "research.universe.include_next": StateChangingActionDefinitionV2(
        "research.universe.include_next", "RESEARCH.UNIVERSE_INCLUDE_NEXT", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.UNIVERSE_CLEAR_OVERRIDE", "RESEARCH_UNIVERSE_INCLUDE",
    ),
    "research.universe.exclude_next": StateChangingActionDefinitionV2(
        "research.universe.exclude_next", "RESEARCH.UNIVERSE_EXCLUDE_NEXT", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.UNIVERSE_CLEAR_OVERRIDE", "RESEARCH_UNIVERSE_EXCLUDE",
    ),
    "research.universe.priority": StateChangingActionDefinitionV2(
        "research.universe.priority", "RESEARCH.UNIVERSE_SET_PRIORITY", "RESEARCH_MAINTENANCE",
        "research:write", "RESEARCH.UNIVERSE_CLEAR_OVERRIDE", "RESEARCH_UNIVERSE_PRIORITY",
    ),
    "paper.request.observation": StateChangingActionDefinitionV2(
        "paper.request.observation", "PAPER.REQUEST_OBSERVATION", "PAPER_OPERATIONS",
        "paper:write", "PAPER.CANCEL_PENDING_REQUEST", "PAPER_OBSERVATION",
    ),
    "operator.decision.acknowledge": StateChangingActionDefinitionV2(
        "operator.decision.acknowledge", "OPERATOR.ACKNOWLEDGE_DECISION", "OPERATOR_FEEDBACK",
        "operator:write", "OPERATOR.CANCEL_PENDING_ACKNOWLEDGEMENT", "OPERATOR_DECISION_ACKNOWLEDGE",
    ),
    "operator.decision.measure": StateChangingActionDefinitionV2(
        "operator.decision.measure", "OPERATOR.MEASURE_DECISION", "OPERATOR_FEEDBACK",
        "operator:write", "OPERATOR.CANCEL_PENDING_MEASUREMENT", "OPERATOR_DECISION_MEASURE",
    ),
})


def resolve_state_changing_action_v2(action_id: str) -> StateChangingActionDefinitionV2:
    try:
        return _DEFINITIONS[action_id]
    except KeyError as exc:
        raise ValueError(f"STATE_CHANGING_ACTION_UNKNOWN:{action_id}") from exc


def state_changing_action_definitions_v2() -> tuple[StateChangingActionDefinitionV2, ...]:
    return tuple(_DEFINITIONS.values())


class PostgresCommandRequestHandlerV2:
    def execute(self, intent: ActionIntentV2) -> str:
        definition = resolve_state_changing_action_v2(intent.action_id)
        if intent.command_code != definition.command_code:
            raise ValueError("STATE_CHANGING_COMMAND_MISMATCH")
        request_id = str(intent.idempotency_key)
        with psycopg2.connect("postgresql:///finam_core") as connection:
            with connection.cursor() as cursor:
                process_id = None
                if definition.request_kind in {"EDGE_SEARCH_RUN", "RESEARCH_REFRESH"}:
                    try:
                        candidate_process_id = str(UUID(str(intent.target_id)))
                    except (TypeError, ValueError, AttributeError):
                        candidate_process_id = request_id
                    cursor.execute(
                        "SELECT recommendation_code FROM marketcore_action.research_process_v1 WHERE process_id=%s::uuid",
                        (candidate_process_id,),
                    )
                    existing = cursor.fetchone()
                    process_id = candidate_process_id if existing is not None else request_id
                    recommendation = (
                        str(existing[0]) if existing is not None else
                        ("KEEP_GATES_AND_EXPAND_EVIDENCE" if definition.request_kind == "EDGE_SEARCH_RUN" else "WAIT_FOR_SYSTEM_ANALYSIS")
                    )
                    cursor.execute(
                        """
                        INSERT INTO marketcore_action.research_process_v1 (
                            process_id,process_type,actor_id,recommendation_code,selected_action_id,
                            command_request_id,status_code,progress_pct,current_step_code,
                            requested_at,started_at,finished_at,updated_at
                        ) VALUES (%s::uuid,%s,%s,%s,%s,%s,'PENDING',0,'QUEUED',
                                  clock_timestamp(),NULL,NULL,clock_timestamp())
                        ON CONFLICT (process_id) DO UPDATE SET
                            process_type=EXCLUDED.process_type,
                            actor_id=EXCLUDED.actor_id,
                            selected_action_id=EXCLUDED.selected_action_id,
                            command_request_id=EXCLUDED.command_request_id,
                            status_code='PENDING',progress_pct=0,current_step_code='QUEUED',
                            outcome_code=NULL,reason_code=NULL,explanation_ru=NULL,
                            requested_at=clock_timestamp(),started_at=NULL,finished_at=NULL,
                            updated_at=clock_timestamp()
                        """,
                        (process_id,
                         "EDGE_SEARCH" if definition.request_kind == "EDGE_SEARCH_RUN" else "RESEARCH_REFRESH",
                         intent.actor_id,recommendation,intent.action_id,request_id),
                    )
                    cursor.execute(
                        """INSERT INTO marketcore_action.research_process_event_v1
                           (process_id,event_code,status_code,progress_pct,step_code,payload)
                           VALUES(%s::uuid,'ACTION_SELECTED','PENDING',0,'QUEUED',
                                  jsonb_build_object('action_id',%s,'request_id',%s))""",
                        (process_id,intent.action_id,request_id),
                    )
                cursor.execute(
                    """
                    INSERT INTO marketcore_action.command_request_v2 (
                        request_id,action_id,request_kind,command_code,actor_id,target_id,status,requested_at,process_id
                    ) VALUES (%s,%s,%s,%s,%s,%s,'PENDING',clock_timestamp(),%s::uuid)
                    ON CONFLICT DO NOTHING
                    RETURNING request_id
                    """,
                    (request_id, intent.action_id, definition.request_kind, definition.command_code,
                     intent.actor_id, intent.target_id, process_id),
                )
                row = cursor.fetchone()
                if row is None:
                    cursor.execute("""SELECT request_id FROM marketcore_action.command_request_v2
                        WHERE request_kind=%s AND status IN ('PENDING','RUNNING')
                        ORDER BY requested_at LIMIT 1""",(definition.request_kind,))
                    active=cursor.fetchone()
                    if active is None:
                        raise ValueError("COMMAND_REQUEST_DUPLICATE")
                    request_id=str(active[0])
        return request_id
