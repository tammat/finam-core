from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_plan_is_db_driven_idempotent_and_gate_preserving() -> None:
    source = (ROOT / "src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert "edge_search_algorithm_analysis_v1" in source
    assert "edge_next_research_plan_v1" in source
    assert "edge_next_research_plan_item_v1" in source
    assert "uuid.uuid5" in source
    assert '"gate_policy": row["gate_policy"]' in source
    assert "pass_gate_snapshot" in source
    assert "ON CONFLICT (parent_run_id,generator_version)" in source


def test_migration_enforces_immutable_pass_gate() -> None:
    sql = (ROOT / "sql/analytics/078_edge_next_research_plan_v1.sql").read_text()
    assert "EDGE_PLAN_PASS_GATE_MISMATCH" in sql
    assert "EDGE_PLAN_PASS_GATE_IMMUTABLE" in sql
    assert "NEW.pass_gate_snapshot IS DISTINCT FROM registry_gate" in sql
    assert "md5(NEW.pass_gate_snapshot::text)" in sql


def test_fail_reasons_have_bounded_adaptations() -> None:
    source = (ROOT / "src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    for reason in (
        "INSUFFICIENT_TRADES",
        "NEGATIVE_COST_ADJUSTED_EXPECTANCY",
        "PROFIT_FACTOR_BELOW_GATE",
        "WALKFORWARD_FOLDS_UNSTABLE",
        "FINAL_HOLDOUT_FAILED",
    ):
        assert reason in source
    assert "MAX_NEW_SCENARIOS" in source
    assert "MAX_VARIANTS_PER_ITEM" in source
    assert "FUTURE_DATA_ONLY" in source
