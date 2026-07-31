from pathlib import Path


def test_funnel_double_click_opens_stage_recommendations() -> None:
    source = Path("src/marketcore/presentation/ui_runtime/assets/v2/browser_platform_driver_v2.js").read_text()
    assert 'sourceElement.dataset.mcActionKind === "NAVIGATE"' in source
    assert "this.openFunnelActions(sourceElement)" in source
    assert 'dialog.setAttribute("data-mc-action-dialog", "funnel")' in source
    assert 'title.textContent = "Рекомендуемые действия"' in source
    assert 'interactionKind: "DOUBLE_CLICK"' in source
    assert source.count("dialog.close();") >= 2
    handler_start = source.index('open.addEventListener("click"')
    assert source.index("dialog.close();", handler_start) < source.index("await this.actionSink", handler_start)
    assert '"Вневыборочная проверка"' in source
    assert '"Форвардное наблюдение"' in source


def test_operator_and_funnel_headers_use_status() -> None:
    migration = Path("sql/presentation/072_operator_status_header_i18n_v1.sql").read_text()
    assert "'column.operator.verdict','ru','Статус','Статус','Статус'" in migration


def test_signal_funnel_separates_today_from_history() -> None:
    source = Path(
        "src/marketcore/presentation/workspace_v2/edge_oos_control_center_v1.py"
    ).read_text()
    assert "Независимые сигналы" in source
    assert "Почему независимые сигналы не дошли до Paper" in source
    assert "Историческая техническая воронка" in source
    assert "date_bin(interval '30 minutes'" in source
    assert "entry_exit_signal_shadow_pair_v2" in source
    assert "v5_oos_observation_audit_v1" in source
