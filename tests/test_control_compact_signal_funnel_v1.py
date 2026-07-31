from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESOLVER = ROOT / "src/marketcore/presentation/workspace_v2/resolver/control_compact_v3_resolver.py"
RENDERER = ROOT / "src/marketcore/presentation/workspace_v2/renderer/control_compact_v3_domain_renderer.py"


def test_compact_control_reads_latest_unique_signal_funnel() -> None:
    source = RESOLVER.read_text(encoding="utf-8")
    assert "signal_funnel_snapshot_v1" in source
    assert "signal_funnel_reason_snapshot_v1" in source
    assert '"signal_funnel_stages": signal_funnel_stages' in source
    assert '"signal_funnel_reasons": signal_funnel_reasons' in source


def test_compact_control_explains_stages_and_non_edge_losses() -> None:
    source = RENDERER.read_text(encoding="utf-8")
    assert "Воронка независимых сигналов" in source
    assert "Одна возможность = инструмент + направление + стратегия + таймфрейм + закрытый бар" in source
    assert "Штатная защита — не потеря edge" in source
    assert "Технические потери — исправлять" in source
    assert "Допущено в Paper" in source
    assert "_signal_funnel_section(snapshot)" in source
