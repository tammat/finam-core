from pathlib import Path

from scripts.generate_adaptive_edge_search_scenarios_v1 import REASON_POLICY,adapted_grid


ROOT=Path(__file__).resolve().parents[1]


def test_every_methodology_gate_has_an_allowed_response() -> None:
    expected={
        "METHODOLOGY_STATISTICAL_SIGNIFICANCE":"EXPAND_FUTURE_EVIDENCE",
        "METHODOLOGY_PARAMETER_ROBUSTNESS":"LOCAL_PARAMETER_NEIGHBORHOOD",
        "METHODOLOGY_INDEPENDENT_HOLDOUT":"NEW_CLEAN_HOLDOUT",
        "METHODOLOGY_REALISTIC_EXECUTION":"STRENGTHEN_SIGNAL_SAME_COSTS",
        "METHODOLOGY_CAPACITY":"LIQUIDITY_PEER_MARKET",
        "METHODOLOGY_PORTFOLIO_CONTRIBUTION":"DIVERSIFY_MARKET_EXPOSURE",
    }
    assert {reason:REASON_POLICY[reason][0] for reason in expected} == expected


def test_new_holdout_keeps_parameters_unchanged() -> None:
    base={"lookback":40,"hold":5,"threshold":1.5,"commission":10,"slippage":2}
    assert adapted_grid([base],"METHODOLOGY_INDEPENDENT_HOLDOUT") == [
        {"lookback":40,"hold":5,"threshold":1.5}
    ]


def test_execution_response_changes_hypothesis_not_costs() -> None:
    grid=adapted_grid([{"lookback":40,"hold":8,"threshold":1.0,"transaction_cost_bps":8}],
                      "METHODOLOGY_REALISTIC_EXECUTION")
    assert grid
    assert all("transaction_cost_bps" not in item for item in grid)
    assert max(item["threshold"] for item in grid) > 1.0
    assert min(item["hold"] for item in grid) < 8


def test_generator_reads_base_pass_methodology_failures_and_is_idempotent() -> None:
    source=(ROOT/"src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert "edge_methodology_evaluation_v1" in source
    assert "base_walkforward_pass" in source
    assert "edge_methodology_research_lineage_v1" in source
    assert "ON CONFLICT(evaluation_id,gate_code) DO NOTHING" in source
    assert "selection_uses_final_holdout\": False" in source
    assert "liquid_peer" in source


def test_generator_uses_the_first_recorded_gate_failure_not_raw_booleans() -> None:
    source=(ROOT/"src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert "jsonb_each_text(coalesce(m.evidence->'gate_statuses'" in source
    assert "WHEN 'STATISTICAL_SIGNIFICANCE' THEN 1" in source
    assert "WHEN 'REALISTIC_EXECUTION' THEN 4" in source


def test_database_contract_forbids_gate_weakening() -> None:
    migration=(ROOT/"sql/analytics/095_methodology_fail_research_generator_v2.sql").read_text()
    for forbidden in ("pass_gate","methodology_contract","execution_costs","consumed_holdout"):
        assert forbidden in migration
    assert "METHODOLOGY_RESEARCH_LINEAGE_IMMUTABLE" in migration
    assert "pass_gate_snapshot" in migration
    assert "holdout_policy" in migration
