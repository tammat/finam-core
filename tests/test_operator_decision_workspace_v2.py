from pathlib import Path


def test_unverified_decisions_cannot_be_green_or_autonomous() -> None:
    migration = Path("sql/analytics/060_operator_decision_workspace_v2.sql").read_text()
    assert "CHECK (policy_verdict IN ('REVIEW_REQUIRED','BLOCKED'))" in migration
    assert "CHECK (quality_code='UNVERIFIED')" in migration
    assert "'ALLOWED'" not in migration


def test_decision_contains_required_evidence_and_rollback_fields() -> None:
    migration = Path("sql/analytics/060_operator_decision_workspace_v2.sql").read_text()
    for field in ("evidence JSONB", "source_as_of", "expected_profit_impact", "risk_impact_code", "confidence", "sample_sufficiency_code", "expires_at", "rollback_plan_code", "actual_result", "feedback_status"):
        assert field in migration
