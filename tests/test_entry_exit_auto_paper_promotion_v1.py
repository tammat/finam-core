from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BUILDER = ROOT / "src/scripts/analytics/build_entry_exit_optimizer_v1.py"
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/home_compact_v1_domain_renderer.py"


def test_challenger_promotes_only_to_paper_automatically():
    source = BUILDER.read_text(encoding="utf-8")
    assert 'stage == "READY_FOR_CHAMPION_CONFIRMATION"' in source
    assert "'AUTO_CHAMPION_CHALLENGER'" in source
    assert "execution_mode='paper'" in source
    assert "AUTO_PAPER_ONLY" in source
    assert "AUTO_ROLLBACK" in source
    assert "consecutive_degraded_cycles" in source
    assert "REAL_TRADING_ENABLED" not in source


def test_optimizer_ui_is_read_only_without_decision_buttons():
    source = RENDERER.read_text(encoding="utf-8")
    start = source.index("def _optimizer_section(")
    end = source.index("\ndef ", start + 10)
    body = source[start:end]
    assert "RenderNodeTypeV2.ACTION" not in body
    assert "назначает победителя" in body
    assert "откатывает Paper" in body
