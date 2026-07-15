from pathlib import Path


def test_shadow_labels_are_loaded_from_i18n() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_renderer.py"
    ).read_text(encoding="utf-8")
    for english_fragment in ("Eligible family-paths", "Quality pending", "Exploratory family-paths", "Активный cohort"):
        assert english_fragment not in source
    assert 'i18n.text("research.shadow.title")' in source
    assert 'i18n.text("research.shadow.eligible_paths")' in source


def test_entry_parameters_and_codes_are_loaded_from_i18n() -> None:
    source = (
        Path(__file__).resolve().parents[1]
        / "src/marketcore/presentation/workspace_v2/renderer/control_center_v2_renderer.py"
    ).read_text(encoding="utf-8")
    assert "def _parameter_text" in source
    assert "research.parameter." in source
    assert "strategy.{_resource_code" in source
    assert "status.{_resource_code" in source
