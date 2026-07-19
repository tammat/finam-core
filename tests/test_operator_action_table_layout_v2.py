from pathlib import Path


def test_operator_table_has_fixed_compact_column_layout() -> None:
    css = Path("src/marketcore/presentation/ui_runtime/assets/v2/workspace_v2.css").read_text()
    assert '[data-mc-node-id="home.operator.actions.table"] { width: 100%; min-width: 0; table-layout: fixed; }' in css
    assert ":nth-child(1) { width: 4%; }" in css
    assert ":nth-child(5) { width: 10%; white-space: nowrap; overflow: hidden; }" in css
    assert ":nth-child(6) { width: 14%; white-space: nowrap; }" in css
    assert ":nth-child(7) { width: 15%; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }" in css


def test_confidence_header_is_abbreviated() -> None:
    migration = Path("sql/presentation/070_operator_action_compact_confidence_i18n_v1.sql").read_text()
    assert "'column.operator.confidence','ru','Увер.'" in migration
