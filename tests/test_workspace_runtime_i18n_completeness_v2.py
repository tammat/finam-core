from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = ROOT / "sql/analytics/148_workspace_runtime_i18n_completeness_v2.sql"


def test_runtime_i18n_covers_navigation_and_signal_loss_keys() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    for key in (
        "research.domain.research.tooltip",
        "workspace.loading",
        "research.domain.quotes.tooltip",
        "status.checkpointed",
        "status.edge_regime_discovery_checkpointed",
        "status.skipped",
        "status.rejection_reason_or_status",
        "status.cluster_block:energy",
        "status.runtime_strategy_blocked:стратегия_заблокирована_по_статистике",
        "status.trend_flip_block",
    ):
        assert key in source


def test_runtime_i18n_is_idempotent() -> None:
    source = MIGRATION.read_text(encoding="utf-8")
    assert "ON CONFLICT(resource_key,locale_code) DO UPDATE" in source
