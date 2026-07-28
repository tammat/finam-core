from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
BOOTSTRAP = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"


def test_outcome_groups_and_hypothesis_linkages_are_russian() -> None:
    source = RENDERER.read_text(encoding="utf-8")
    for raw, russian in (
        ("PREMARKET", "До открытия"),
        ("VWAP_BANDS_MR", "Возврат к VWAP"),
        ("VOLATILITY_BREAKOUT_EQUITY", "Пробой волатильности"),
        ("SHORT", "Продажа"),
        ("STOP_TAKE", "Стоп или цель"),
        ("FRESH_SAMPLE_BELOW_80", "Накопить 80 свежих сделок"),
    ):
        assert raw in source
        assert russian in source
    assert "_research_value_label(item.dimension_value)" in source


def test_large_research_tables_are_collapsible_and_stateful() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "installResearchTableFolds" in source
    assert '"research-outcomes"' in source
    assert '"research-hypotheses"' in source
    assert "details.dataset.mcSectionGroup = code" in source
    assert "installResearchTableFolds();" in source
    assert "restorePanelState(stateToRestore" in source
