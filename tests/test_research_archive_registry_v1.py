from pathlib import Path


SQL = (Path(__file__).parents[1] / "sql/analytics/191_research_archive_registry_v1.sql").read_text()


def test_archive_is_logical_and_does_not_delete_source_data() -> None:
    assert "research_archive_registry_v1" in SQL
    assert "DELETE FROM public.closed_trades" not in SQL
    assert "DELETE FROM analytics.trade_outcome_hypothesis_v1" not in SQL


def test_legacy_cohorts_and_invalid_x_are_archived() -> None:
    assert "LEGACY_DERIVED" in SQL
    assert "LEGACY_NO_CONTEXT" in SQL
    assert "INVALID_SYMBOL_X_REPLACED_BY_X5" in SQL


def test_active_views_exclude_registry_entries() -> None:
    assert "closed_trades_active_v3" in SQL
    assert "trade_outcome_hypothesis_active_v3" in SQL
    assert SQL.count("NOT EXISTS") >= 2
