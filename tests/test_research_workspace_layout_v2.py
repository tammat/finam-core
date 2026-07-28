from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/research_v2_domain_renderer.py"
BOOTSTRAP = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_shell_bootstrap_v2.js"
CSS = ROOT / "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"


def test_research_first_screen_has_five_operating_metrics() -> None:
    source = RENDERER.read_text(encoding="utf-8")
    tile_block = source.split("tiles=(", 1)[1].split("governance_tiles=", 1)[0]
    assert tile_block.count("_tile(") == 4
    assert "_oos_waiting_card(s)" in tile_block
    for code in ("live_signals", "paper_fills", "closed_trades", "oos_pass"):
        assert f'_tile("{code}"' in tile_block
    for code in ("instruments", "candidates", "regime_progress", "queue"):
        assert f'_tile("{code}"' not in tile_block


def test_research_details_are_grouped_by_operator_task() -> None:
    source = BOOTSTRAP.read_text(encoding="utf-8")
    assert "installResearchWorkspaceLayout" in source
    for label in (
        "OOS и методология",
        "Инструменты и рынки",
        "Результаты и гипотезы",
        "Диагностика",
    ):
        assert label in source
    assert "installResearchWorkspaceLayout();" in source
    assert "mc-research-disclosure-grid" in source


def test_research_layout_is_compact_and_responsive() -> None:
    source = CSS.read_text(encoding="utf-8")
    assert ".mc-research-now" in source
    assert ".mc-research-disclosure-grid" in source
    assert "grid-template-columns: repeat(5, minmax(0, 1fr))" in source
    assert "@media (max-width: 760px)" in source
    assert ".mc-research-work-group[open]" in source
