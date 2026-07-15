from marketcore.action.handler_registry_v2 import state_changing_action_definitions_v2


def test_only_safe_research_and_paper_requests_are_registered() -> None:
    definitions = state_changing_action_definitions_v2()
    assert {item.request_kind for item in definitions} == {"RESEARCH_REFRESH", "PAPER_OBSERVATION"}
    encoded = repr(definitions).upper()
    for forbidden in ("BROKER", "LIVE", "ORDER", "KILL_SWITCH", "RISK_LIMIT"):
        assert forbidden not in encoded
