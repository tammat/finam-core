from pathlib import Path

from scripts.generate_temporal_oos_branches_v1 import fingerprint, temporal_parameters


ROOT = Path(__file__).resolve().parents[1]


def test_temporal_parameters_require_one_predeclared_session() -> None:
    base = {"lookback": 20, "hold": 5, "threshold": 1.5, "transaction_cost_bps": 0}
    overlay = {"entry_policy_code": "META_ENTRY_V2", "exit_policy_code": "DYNAMIC_EXIT_V1"}
    result = temporal_parameters(base, overlay, "US_OPEN")
    assert result["entry_session_mode"] == "REQUIRE"
    assert result["entry_allowed_sessions"] == ["US_OPEN"]
    assert result["session_analysis"] == "MARKET_SESSION_CONTRACT_V1"
    assert result["exit_policy_code"] == "DYNAMIC_EXIT_V1"
    assert "transaction_cost_bps" not in result


def test_temporal_fingerprint_separates_sessions() -> None:
    first = temporal_parameters({"lookback": 20, "hold": 5, "threshold": 1.5}, {}, "MOEX_OPEN")
    second = temporal_parameters({"lookback": 20, "hold": 5, "threshold": 1.5}, {}, "US_OPEN")
    assert fingerprint("EMA_TREND", "SBER@MISX", first) != fingerprint(
        "EMA_TREND", "SBER@MISX", second
    )


def test_temporal_generator_is_db_driven_future_only_and_checkpointed() -> None:
    migration = (ROOT / "sql/analytics/177_temporal_oos_branches_v1.sql").read_text()
    generator = (ROOT / "src/scripts/generate_temporal_oos_branches_v1.py").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    checkpoint = (ROOT / "src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    assert "temporal_oos_session_policy_v1" in migration
    assert "temporal_oos_algorithm_policy_v1" in migration
    assert "pass_gates_unchanged" in generator
    assert '"cost_model_unchanged": True' in generator
    assert '"fold_overlap_forbidden": True' in generator
    assert '"confirmation_mode": "FUTURE_DATA_ONLY"' in generator
    assert "TEMPORAL_OOS_BRANCH_GENERATOR_V1" in scheduler
    assert "c.branch_code" in checkpoint


def test_temporal_branch_is_visible_on_research_panel() -> None:
    migration = (ROOT / "sql/analytics/177_temporal_oos_branches_v1.sql").read_text()
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    assert "research.remediation.branch.temporal_session" in migration
    assert "WHEN 'TEMPORAL_SESSION' THEN 3" in resolver
