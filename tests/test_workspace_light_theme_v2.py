from pathlib import Path


CSS_PATH = Path(
    "src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css"
)


def test_workspace_uses_neutral_semantic_theme_tokens() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    for token in (
        "--mc-page:",
        "--mc-surface:",
        "--mc-text-primary:",
        "--mc-text-secondary:",
        "--mc-border:",
        "--mc-action:",
        "--mc-ok:",
        "--mc-warning:",
        "--mc-danger:",
    ):
        assert token in css
    assert "color-scheme: light" in css
    assert "background: var(--mc-page)" in css


def test_wide_home_layout_is_readable_without_reintroducing_metric_noise() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    assert "@media (min-width: 1440px)" in css
    assert ":root { font-size: 19px; }" in css
    assert '[data-mc-node-id="home.operator.section.grid"]' in css
    assert "grid-template-columns: repeat(3, minmax(0, 1fr))" in css
    assert '[data-mc-node-id="home.section.operating_traffic.grid"]' in css


def test_control_center_uses_large_progressive_disclosure_cards() -> None:
    css = CSS_PATH.read_text(encoding="utf-8")
    assert ".mc-control-group-grid" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr))" in css
    assert '[data-mc-section-group][open] { grid-column: 1 / -1; }' in css
    assert "min-height: 142px" in css
    assert "@media (max-width: 900px)" in css
