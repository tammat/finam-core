from pathlib import Path


def test_research_runtime_translation_patch_covers_render_tree_keys() -> None:
    sql = Path("sql/analytics/100_research_runtime_i18n_completeness_v1.sql").read_text()
    for key in (
        "research.domain.selected.tooltip",
        "research.domain.excluded.tooltip",
        "research.domain.skipped",
        "research.domain.skipped.tooltip",
        "research.domain.edge_search_executor_failed.methodology_gate",
        "research.domain.edge_search_executor_failed.methodology_gate.tooltip",
        "research.domain.edge_search_server_load_high",
        "research.domain.edge_search_server_load_high.tooltip",
        "research.domain.donchian_trend_expansion.tooltip",
        "research.domain.intermarket_sber_spread.tooltip",
        "research.domain.relative_strength.tooltip",
    ):
        assert key in sql
    assert "ON CONFLICT(resource_key,locale_code) DO UPDATE" in sql
