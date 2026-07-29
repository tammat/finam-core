from pathlib import Path


def test_compact_home_has_iphone_single_column_contract() -> None:
    css=Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert "@media (max-width: 600px)" in css
    assert '[data-mc-node-id="home.compact.workspace"]' in css
    assert 'grid-template-columns: 1fr' in css
    assert 'overflow-wrap: anywhere' in css
    assert '[data-mc-node-id="home.compact.refresh"] { min-height: 48px' in css
