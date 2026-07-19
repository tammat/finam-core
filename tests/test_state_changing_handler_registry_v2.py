from pathlib import Path

from marketcore.action.handler_registry_v2 import state_changing_action_definitions_v2


def test_only_safe_non_execution_requests_are_registered() -> None:
    definitions = state_changing_action_definitions_v2()
    assert {"RESEARCH_REFRESH", "EDGE_SEARCH_RUN", "PAPER_OBSERVATION", "OPERATOR_DECISION_ACKNOWLEDGE", "OPERATOR_DECISION_MEASURE"} <= {item.request_kind for item in definitions}
    encoded = repr(definitions).upper()
    for forbidden in ("BROKER", "LIVE", "ORDER", "KILL_SWITCH", "RISK_LIMIT"):
        assert forbidden not in encoded


def test_long_research_commands_reuse_active_request() -> None:
    source = Path("src/marketcore/action/handler_registry_v2.py").read_text(encoding="utf-8")
    assert "active_request = cursor.fetchone()" in source
    assert "return str(active_request[0])" in source
