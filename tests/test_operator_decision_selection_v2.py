from pathlib import Path


def test_acknowledgement_is_registered_without_execution_terms() -> None:
    source = Path("src/marketcore/action/handler_registry_v2.py").read_text()
    assert "operator.decision.acknowledge" in source
    assert "OPERATOR_DECISION_ACKNOWLEDGE" in source


def test_worker_only_acknowledges_review_required_decision() -> None:
    source = Path("src/marketcore/action/command_worker_v2.py").read_text()
    assert "policy_verdict='REVIEW_REQUIRED'" in source
    assert "selection_status='NOT_SELECTED'" in source
    assert "INSERT INTO public.orders" not in source
