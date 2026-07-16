from pathlib import Path


def test_command_request_schema_accepts_operator_decisions() -> None:
    migration = Path("sql/marketcore_action/005_operator_decision_command_request_v2.sql").read_text()
    assert "OPERATOR_DECISION_ACKNOWLEDGE" in migration
    assert "OPERATOR_DECISION_MEASURE" in migration
    assert "OPERATOR.ACKNOWLEDGE_DECISION" in migration
    assert "OPERATOR.MEASURE_DECISION" in migration
