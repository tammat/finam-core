import json
from uuid import uuid4

import psycopg2

from marketcore.presentation.action_http_controller_v2 import dispatch_browser_action_http_v2


def test_navigation_reaches_governed_dispatcher_and_audit() -> None:
    action_id = f"navigation.integration.{uuid4()}"
    response = dispatch_browser_action_http_v2(json.dumps({
        "actionId": action_id,
        "actionKind": "NAVIGATE",
        "interactionKind": "CLICK",
        "targetId": "container.risk",
    }).encode())
    payload = json.loads(response.body)
    assert response.status_code == 200
    assert payload["status"] == "NAVIGATED" and payload["target_id"] == "container.risk"
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT status,reason_code FROM marketcore_action.action_audit_v2 WHERE action_id=%s ORDER BY audit_id DESC LIMIT 1", (action_id,))
            assert cursor.fetchone() == ("NAVIGATED", "NAVIGATION_ALLOWED")


def test_state_changing_browser_action_is_not_registered() -> None:
    response = dispatch_browser_action_http_v2(json.dumps({
        "actionId": "research.unknown",
        "actionKind": "COMMAND",
        "interactionKind": "DOUBLE_CLICK",
        "commandCode": "RESEARCH.REFRESH",
    }).encode())
    assert response.status_code == 403
    assert json.loads(response.body)["reason_code"] == "STATE_CHANGING_ACTION_NOT_REGISTERED"


def test_registered_research_action_creates_pending_request() -> None:
    request_id = str(uuid4())
    response = dispatch_browser_action_http_v2(json.dumps({
        "actionId": "research.request.refresh", "actionKind": "COMMAND",
        "interactionKind": "DOUBLE_CLICK", "requestId": request_id,
    }).encode())
    payload = json.loads(response.body)
    assert response.status_code == 202 and payload["status"] == "ACCEPTED"
    assert payload["request_status"] == "PENDING"
    with psycopg2.connect("postgresql:///finam_core") as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT request_kind,status FROM marketcore_action.command_request_v2 WHERE request_id=%s", (request_id,))
            assert cursor.fetchone() == ("RESEARCH_REFRESH", "PENDING")


def test_unknown_navigation_target_is_denied() -> None:
    response = dispatch_browser_action_http_v2(json.dumps({
        "actionId": "navigation.open.diagnostic",
        "actionKind": "NAVIGATE",
        "interactionKind": "CLICK",
        "targetId": "container.diagnostic",
    }).encode())
    assert response.status_code == 400
    assert json.loads(response.body)["reason_code"] == "NAVIGATION_ACTION_INVALID"
