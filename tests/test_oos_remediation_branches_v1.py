from pathlib import Path

from scripts.generate_oos_remediation_branches_v1 import (
    BRANCH_POLICY,
    FOCUS_ALGORITHM_BUDGET,
    fingerprint,
)


ROOT = Path(__file__).resolve().parents[1]


def test_branch_budgets_are_bounded_and_costs_get_priority() -> None:
    assert BRANCH_POLICY["COST_REMEDIATION"]["budget"] == 34
    assert BRANCH_POLICY["SAMPLE_EXPANSION"]["budget"] == 10
    assert sum(item["budget"] for item in BRANCH_POLICY.values()) == 44
    assert FOCUS_ALGORITHM_BUDGET == {
        "DONCHIAN_VOL_BREAKOUT": 20,
        "EMA_TREND": 14,
    }
    assert sum(FOCUS_ALGORITHM_BUDGET.values()) == BRANCH_POLICY["COST_REMEDIATION"]["budget"]


def test_fingerprint_ignores_runtime_scenario_identity() -> None:
    base = {"lookback": 20, "hold": 5, "threshold": 1.5}
    enriched = {**base, "adaptive_scenario_id": "00000000-0000-0000-0000-000000000001"}
    assert fingerprint("EMA_TREND", "SBER@MISX", base) == fingerprint("EMA_TREND", "SBER@MISX", enriched)


def test_generator_preserves_pass_gates_and_is_db_scheduled() -> None:
    generator = (ROOT / "src/scripts/generate_oos_remediation_branches_v1.py").read_text()
    migration = (ROOT / "sql/analytics/158_oos_remediation_branches_v1.sql").read_text()
    scheduler = (ROOT / "src/scripts/run_db_job_scheduler_v1.py").read_text()
    assert '"gate_policy": row["gate_policy"]' in generator
    assert '"cost_model_unchanged": True' in generator
    assert '"selection_uses_final_holdout": False' in generator
    assert "OOS_REMEDIATION_BRANCH_GENERATOR_V1" in migration
    assert "OOS_REMEDIATION_BRANCH_GENERATOR_V1" in scheduler


def test_panel_exposes_created_pruned_and_oos_pass() -> None:
    snapshot = (ROOT / "src/marketcore/presentation/workspace_v2/domain/research_snapshot_v2.py").read_text()
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert "OosRemediationBranchV1" in snapshot
    assert "oos_remediation_branch_panel_v1" in resolver
    for metric in ("created", "pruned", "pass"):
        assert f'research.remediation.{{index}}.{metric}' in renderer


def test_zero_cost_diagnostic_is_visible_but_cannot_promote() -> None:
    migration = (ROOT / "sql/analytics/159_zero_cost_diagnostic_v1.sql").read_text()
    runner = (ROOT / "src/scripts/run_checkpointed_walkforward_v4.py").read_text()
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py").read_text()
    assert "ZERO_COST_DIAGNOSTIC" in migration
    assert "diagnostic_only" in migration
    assert '"promotion_allowed":False' in runner
    assert '"runtime_allowed":False' in runner
    assert "RESEARCH.REQUEST_REFRESH" in renderer


def test_resource_policy_reserves_temporal_budget_and_dynamic_exit() -> None:
    migration = (ROOT / "sql/analytics/159_zero_cost_diagnostic_v1.sql").read_text()
    temporal = (ROOT / "sql/analytics/177_temporal_oos_branches_v1.sql").read_text()
    adaptive = (ROOT / "src/scripts/generate_adaptive_edge_search_scenarios_v1.py").read_text()
    assert "('COST_REMEDIATION',70,34" in migration
    assert "('SAMPLE_EXPANSION',20,10" in migration
    assert "('NEW_INSTRUMENT_EXPLORATION',10,4" in migration
    assert "('TEMPORAL_SESSION',10,10,15" in temporal
    assert "SET resource_share_pct=60" in temporal
    assert adaptive.count('"exit_max_holding_bars": 20') >= 2
    assert '"entry_volume_mode": "REQUIRE"' in adaptive
    assert adaptive.count('"entry_regime_mode": "REQUIRE"') >= 2
    assert '"entry_allowed_regimes"' in adaptive


def test_workspace_navigation_updates_browser_url() -> None:
    shell = (ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js").read_text()
    assert "ROUTE_BY_TARGET" in shell
    assert 'history[method]({marketcoreTargetId: targetId}' in shell
    assert 'addEventListener("popstate"' in shell
