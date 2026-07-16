from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

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
                cursor.execute(
                    """
                    INSERT INTO marketcore_action.command_request_v2 (
                        request_id,action_id,request_kind,command_code,actor_id,target_id,status,requested_at
                    ) VALUES (%s,%s,%s,%s,%s,%s,'PENDING',clock_timestamp())
                    ON CONFLICT (request_id) DO NOTHING
                    RETURNING request_id
                    """,
                    (request_id, intent.action_id, definition.request_kind, definition.command_code, intent.actor_id, intent.target_id),
                )
                row = cursor.fetchone()
                if row is None:
                    raise ValueError("COMMAND_REQUEST_DUPLICATE")
        return request_id
