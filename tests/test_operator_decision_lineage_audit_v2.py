from pathlib import Path


def test_lineage_audit_is_append_only_and_idempotent() -> None:
    migration = Path("sql/analytics/063_operator_decision_lineage_audit_v2.sql").read_text()
    builder = Path("src/scripts/build_operator_decision_workspace_v2.py").read_text()

    assert "BEFORE UPDATE OR DELETE" in migration
    assert "OPERATOR_DECISION_LINEAGE_AUDIT_APPEND_ONLY" in migration
    assert "UNIQUE (decision_id, lineage_hash)" in migration
    assert "ON CONFLICT (decision_id,lineage_hash) DO NOTHING" in builder


def test_lineage_snapshot_covers_evidence_policy_selection_and_result() -> None:
    migration = Path("sql/analytics/063_operator_decision_lineage_audit_v2.sql").read_text()
    for field in (
        "source_identity", "source_as_of", "evidence JSONB", "policy_verdict",
        "autonomy_mode", "selection_status", "feedback_status", "actual_result",
    ):
        assert field in migration
