from pathlib import Path


def test_validated_edge_uses_exact_candidate_identity() -> None:
    source = Path("src/scripts/build_profit_funnel_transition_lineage_v2.py").read_text()
    assert "v.candidate_uuid=c.candidate_uuid" in source
    assert 'reason_code="CANDIDATE_UUID_FULL_MATCH"' in source


def test_validated_edge_cannot_enable_trading() -> None:
    migration = Path("sql/analytics/056_profit_funnel_validated_edge_v2.sql").read_text()
    assert "CHECK (NOT paper_allowed AND NOT runtime_allowed AND NOT live_allowed)" in migration
