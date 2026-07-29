from __future__ import annotations

from datetime import timezone

from marketcore.presentation.render_tree.v2 import (
    ActionKindV2, RenderActionV2, RenderContentV2, RenderDocumentV2,
    RenderNodeStateV2, RenderNodeTypeV2, RenderNodeV2, validate_render_document_v2,
)


def _leaf(kind, node_id, value=None, fmt=None, level=None):
    return RenderNodeV2(kind, node_id, content=RenderContentV2(value=value, format_code=fmt, level_code=level))


def _utc(value):
    """В контракте RenderTree время UTC; браузер показывает его в Europe/Moscow."""
    if value is None or value.tzinfo is None:
        return value
    return value.astimezone(timezone.utc)


def _card(code, title, value, detail, status):
    return RenderNodeV2(RenderNodeTypeV2.CARD, f"control.v3.card.{code}",
        state=RenderNodeStateV2(status_code=status), children=(
            _leaf(RenderNodeTypeV2.TITLE, f"control.v3.card.{code}.title", title, level="CARD"),
            _leaf(RenderNodeTypeV2.METRIC_VALUE, f"control.v3.card.{code}.value", value,
                  "INTEGER" if isinstance(value, int) else None),
            _leaf(RenderNodeTypeV2.TEXT, f"control.v3.card.{code}.detail", detail),
        ))


def _metric_row(code, label, value):
    return RenderNodeV2(RenderNodeTypeV2.METRIC_ROW, f"control.v3.process.{code}", children=(
        _leaf(RenderNodeTypeV2.METRIC_LABEL, f"control.v3.process.{code}.label", label),
        _leaf(RenderNodeTypeV2.METRIC_VALUE, f"control.v3.process.{code}.value", value,
              "DECIMAL" if isinstance(value, float) else None),
    ))


def _command(code, label, action_id, command_code, *, target_id=None,
             enabled=True, requires_approval=False, rollback_code=None):
    return RenderNodeV2(
        RenderNodeTypeV2.ACTION,
        f"control.v3.action.{code}",
        content=RenderContentV2(value=label),
        action=RenderActionV2(
            action_id,
            ActionKindV2.COMMAND,
            command_code=command_code,
            policy_class="RESEARCH_MAINTENANCE",
            target_id=target_id,
            enabled=enabled,
            requires_approval=requires_approval,
            reversible=bool(rollback_code),
            rollback_code=rollback_code,
            idempotency_key="client.request",
            blocked_reason_code=None if enabled else "RESEARCH_COMMAND_ALREADY_ACTIVE",
        ),
    )


def _edge_control_section(snapshot):
    state = snapshot["command_state"]
    pending = int(state.get("edge_pending") or 0)
    manual_pending = int(state.get("edge_manual_pending") or 0)
    running = int(state.get("edge_running") or 0)
    refresh_active = int(state.get("refresh_active") or 0)
    active = pending + running
    primary_action = (
        _command("edge_cancel", "Отменить ожидающий запуск", "research.edge_search.cancel",
                 "RESEARCH.CANCEL_EDGE_SEARCH", enabled=True, requires_approval=True)
        if manual_pending > 0 else
        _command("edge_run", "Запустить edge search", "research.edge_search.run",
                 "RESEARCH.RUN_EDGE_SEARCH", enabled=running == 0,
                 rollback_code="RESEARCH.CANCEL_PENDING_REQUEST")
    )
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.edge_control", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.edge_control.title", "Управление поиском edge", level="SECTION"),
        _metric_row("edge_autorun", "Автономный режим",
                    "Включён" if state.get("autorun_enabled") else "Не подтверждён"),
        _metric_row("edge_queue", "Edge search: очередь / выполняется", f"{pending} / {running}"),
        _metric_row("edge_failures", "Ошибок команд за 24 часа", int(state.get("failed_24h") or 0)),
        primary_action,
        _command("refresh", "Обновить research-витрины", "research.request.refresh",
                 "RESEARCH.REQUEST_REFRESH", enabled=refresh_active == 0,
                 rollback_code="RESEARCH.CANCEL_PENDING_REQUEST"),
    ))


def _freshness_section(rows):
    children = [_leaf(RenderNodeTypeV2.TITLE, "control.v3.freshness.title",
                      "Свежесть V5", level="SECTION")]
    for index, row in enumerate(rows, start=1):
        age = int(row.get("age_sec") or 0)
        threshold = 180 if row.get("timeframe") == "M1" else 420
        children.append(RenderNodeV2(
            RenderNodeTypeV2.METRIC_ROW,
            f"control.v3.freshness.{index}",
            state=RenderNodeStateV2(
                status_code="OK" if age <= threshold else "WARNING",
                source_identity="market_bars",
                source_as_of=_utc(row.get("latest_bar")),
            ),
            children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,
                      f"control.v3.freshness.{index}.label",
                      f"{row['symbol']} · {row['timeframe']}"),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,
                      f"control.v3.freshness.{index}.value", age, "INTEGER"),
            ),
        ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.freshness",
                        children=tuple(children))


def _jobs_section(rows):
    running = sum(1 for row in rows if row.get("status_code") == "RUNNING")
    failed = sum(1 for row in rows if row.get("status_code") in {"FAILED", "TIMEOUT"})
    latest = rows[0]["job_code"] if rows else "Нет данных"
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.scheduler", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.scheduler.title", "Автоматический research scheduler", level="SECTION"),
        _metric_row("scheduler_latest", "Последнее задание", latest),
        _metric_row("scheduler_running", "Выполняется", running),
        _metric_row("scheduler_failed", "Ошибок в последних 12", failed),
    ))


def _hierarchy_section(snapshot):
    hierarchy = snapshot.get("hierarchy") or {}
    nearest = snapshot.get("hierarchy_nearest") or {}
    children = [
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.hierarchy.title",
              "Иерархическое evidence V5", level="SECTION"),
    ]
    labels = (
        ("STRATEGY", "Стратегия × scope × timeframe × side"),
        ("INSTRUMENT_SIDE", "Инструмент и направление"),
        ("COMPATIBLE_CONTEXT", "Совместимый контекст"),
        ("EXACT_CONTEXT", "Точный контекст"),
    )
    for code, label in labels:
        row = hierarchy.get(code) or {}
        value = (f"групп {int(row.get('groups') or 0)} · максимум {int(row.get('max_trades') or 0)}"
                 f" · stop {int(row.get('early_stop') or 0)} · OOS {int(row.get('ready') or 0)}")
        children.append(_metric_row(f"hierarchy_{code.lower()}", label, value))
    nearest_text = (
        f"{nearest.get('symbol_code')} · {nearest.get('strategy_code')} · "
        f"{nearest.get('closed_trades',0)} / {nearest.get('target_trades',80)} · "
        f"{nearest.get('decision_code')}"
        if nearest else "Точных V5-групп пока нет"
    )
    children.append(_leaf(RenderNodeTypeV2.TEXT, "control.v3.hierarchy.nearest", nearest_text))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.hierarchy",
                        children=tuple(children))


def _open_positions_section(rows):
    children = [
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.open_positions.title",
              "Открытые учебные позиции", level="SECTION")
    ]
    if not rows:
        children.append(_leaf(RenderNodeTypeV2.TEXT, "control.v3.open_positions.empty",
                              "Открытых исследовательских позиций нет"))
        return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.open_positions",
                            children=tuple(children))
    labels = {
        "WAITING_FIRST_CLOSED_BAR": "ожидается первый закрытый бар",
        "SESSION_IDLE_OR_DATA_STALE": "вне сессии или нет нового бара",
        "CANDLE_EXIT_MONITOR_ACTIVE": "candle-exit активен",
    }
    for index, row in enumerate(rows, start=1):
        monitor = str(row.get("exit_monitor_code") or "UNKNOWN")
        value = (f"{row.get('symbol')} · {int(row.get('bars_held') or 0)} баров · "
                 f"{labels.get(monitor, monitor.lower())}")
        children.append(RenderNodeV2(
            RenderNodeTypeV2.METRIC_ROW,
            f"control.v3.open_positions.{index}",
            state=RenderNodeStateV2(
                status_code="WARNING" if monitor != "CANDLE_EXIT_MONITOR_ACTIVE" else "OK",
                source_identity="analytics.paper_research_position_projection_v1",
                source_as_of=_utc(row.get("last_bar_at") or row.get("opened_at")),
            ),
            children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,
                      f"control.v3.open_positions.{index}.label", str(index)),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,
                      f"control.v3.open_positions.{index}.value", value),
            ),
        ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.open_positions",
                        children=tuple(children))


def _multi_asset_section(rows, cny_spot_controls=()):
    children = [
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.multi_asset.title",
              "Валюты и золото", level="SECTION"),
    ]
    grouped = {}
    for row in rows:
        grouped.setdefault(row.get("asset_code"), []).append(row)
    asset_names = {
        "USD": "Доллар",
        "GOLD": "Золото",
        "CNY": "Юань",
    }
    for index, (asset, branches) in enumerate(grouped.items(), start=1):
        first = branches[0]
        by_clock = {}
        for item in branches:
            clock = str(item.get("timeframe_code"))
            by_clock.setdefault(clock, {})[str(item.get("side_code"))] = int(
                item.get("closed_trades") or 0)
        clock_text = " · ".join(
            f"{clock[1:]}м: П {by_clock.get(clock, {}).get('LONG', 0)} / "
            f"Пр {by_clock.get(clock, {}).get('SHORT', 0)}"
            for clock in ("M1", "M5")
        )
        active = str(first.get("active_timeframe") or "M5").replace("M", "")
        costs_ready = first.get("scalper_fee") is not None and first.get("spread_bps") is not None
        value = (f"сейчас {active} мин · {clock_text} · "
                 f"{'расходы видны' if costs_ready else 'расходы неполные'}")
        children.append(RenderNodeV2(
            RenderNodeTypeV2.METRIC_ROW,
            f"control.v3.multi_asset.{index}",
            state=RenderNodeStateV2(
                status_code="OK" if first.get("research_entry_allowed") else "WARNING",
                source_identity="analytics.v5_asset_branch_policy_v1",
                source_as_of=_utc(first.get("spread_observed_at") or first.get("cost_verified_at")),
            ),
            children=(
                _leaf(RenderNodeTypeV2.METRIC_LABEL,
                      f"control.v3.multi_asset.{index}.label",
                      asset_names.get(asset, asset)),
                _leaf(RenderNodeTypeV2.METRIC_VALUE,
                      f"control.v3.multi_asset.{index}.value", value),
            ),
        ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.multi_asset",
                        children=tuple(children))


def _ru_status(value):
    code = str(value or "").upper()
    return {
        "SKIPPED": "Отложен",
        "RUNNING": "Выполняется",
        "PENDING": "В очереди",
        "QUEUED": "В очереди",
        "SUCCEEDED": "Готово",
        "COMPLETE": "Готово",
        "COMPLETED": "Готово",
        "FAILED": "Требует действия",
        "ERROR": "Требует действия",
        "STALLED": "Требует действия",
        "BLOCKED": "Требует действия",
    }.get(code, str(value or "Нет процесса").replace("_", " "))


def _strategy_ru(value):
    code = str(value or "").upper()
    return {
        "VOLATILITY_BREAKOUT_EQUITY": "Пробой волатильности",
        "MEAN_REVERSION_EQUITY": "Возврат к среднему",
        "BR_CONSERVATIVE_BREAKOUT": "Осторожный пробой нефти",
        "NG_CONSERVATIVE_BREAKOUT_M1": "Осторожный пробой газа",
        "DONCHIAN_VOL_BREAKOUT": "Пробой Дончиана",
        "EMA_TREND": "Тренд EMA",
        "MOMENTUM": "Импульс",
        "RSI": "RSI",
        "VWAP": "Возврат к VWAP",
    }.get(code, str(value or "Неизвестная стратегия").replace("_", " ").title())


def _regime_ru(value):
    code = str(value or "").lower()
    if code in {"", "unknown", "unspecified"}:
        return "Разделять по фактическому режиму"
    return {
        "trend_up_high_vol": "рост · высокая волатильность",
        "trend_down_high_vol": "снижение · высокая волатильность",
        "range_high_vol": "боковик · высокая волатильность",
        "trend_up_low_vol": "рост · низкая волатильность",
        "trend_down_low_vol": "снижение · низкая волатильность",
        "range_low_vol": "боковик · низкая волатильность",
    }.get(code, str(value).replace("_", " "))


def _exit_ru(value):
    return {
        "STOP_TAKE": "Стоп или цель",
        "DYNAMIC_20": "Динамический · до 20 баров",
        "TIME_EXIT": "Выход по времени",
    }.get(str(value or "").upper(), str(value or "Выход не определён").replace("_", " "))


def _profit_factor_ru(value, trades):
    """Show an observed ratio only when both profit and loss are present."""
    trade_count = int(trades or 0)
    if trade_count < 2:
        return "PF — · недостаточно данных"
    if value is None:
        return "PF — · недостаточно данных"
    try:
        profit_factor = float(value)
    except (TypeError, ValueError):
        return "PF — · недостаточно данных"
    # Compatibility with historical snapshots created before the SQL source
    # stopped emitting the artificial no-loss sentinel.
    if profit_factor >= 999:
        return "PF — · нет убыточных сделок"
    return f"PF {profit_factor:.2f}"


def _links_table(scope_code, rows):
    scope_slug = "equity" if scope_code.endswith("EQUITY") else "futures"
    columns = ("Инструмент", "Стратегия", "Контекст", "Архив", "Свежих V5", "Итог V5", "Когорта", "Готовность к OOS")
    header = RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, f"control.v3.{scope_slug}.header", children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"control.v3.{scope_slug}.header.{index}", label)
        for index, label in enumerate(columns, start=1)))
    body = []
    for index, item in enumerate(rows, start=1):
        status = ("OK" if item.get("readiness_code") in {"READY_FOR_OOS", "QUEUED"}
                  else "BLOCKED" if item.get("readiness_code") == "QUARANTINED" else "WARNING")
        technical = " · ".join((scope_code, str(item["symbol"]), str(item["strategy"]), str(item["side"]),
                                str(item["session_code"]), str(item["regime_code"]), str(item["exit_rule"])))
        match_ru = {"EXACT":"Точное", "RELATED":"Связанное", "V5_ONLY":"Новая V5"}.get(
            str(item.get("archive_match_code")), "Нет данных")
        readiness_ru = {
            "WAITING_SAMPLE":"Накопление", "WAITING_CONTEXT":"Нужен контекст",
            "FAILED_FRESH_EVIDENCE":"Не подтверждено", "READY_FOR_OOS":"Готово",
            "QUEUED":"В очереди", "QUARANTINED":"Карантин",
        }.get(str(item.get("readiness_code")), "Нет данных")
        archive_trades = int(item.get("archive_trades") or 0)
        archive_value = (f"{archive_trades} · {_profit_factor_ru(item.get('archive_profit_factor'), archive_trades)}"
                         if item.get("archive_match_code") != "V3_ONLY" else "Нет прямого")
        pnl = float(item.get("fresh_net_pnl") or 0)
        pnl_value = (
            f"{pnl:+,.2f} ₽ · "
            f"{_profit_factor_ru(item.get('fresh_profit_factor'), item.get('accumulated'))}"
        ).replace(",", " ")
        context_value = " · ".join((
            {"LONG":"Покупка", "SHORT":"Продажа"}.get(str(item["side"]).upper(), str(item["side"])),
            str(item["session_code"]).replace("_", " "), _regime_ru(item["regime_code"]),
            _exit_ru(item["exit_rule"]),
        ))
        body.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, f"control.v3.{scope_slug}.row.{index}",
            state=RenderNodeStateV2(status_code=status, source_identity=technical, source_as_of=_utc(item.get("updated_at"))),
            action=RenderActionV2(f"control.v3.{scope_slug}.detail.{index}", ActionKindV2.NAVIGATE,
                                  target_id="container.research", enabled=True),
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.symbol", item["symbol"]),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.strategy", _strategy_ru(item["strategy"])),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.context", context_value),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.archive", archive_value),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.count", f"{item['accumulated']} / {item['target']}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.pnl", pnl_value),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.match", match_ru),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.{scope_slug}.row.{index}.status", readiness_ru),
            )))
    return RenderNodeV2(RenderNodeTypeV2.TABLE, f"control.v3.{scope_slug}.table", children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, f"control.v3.{scope_slug}.head", children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, f"control.v3.{scope_slug}.body", children=tuple(body)),
    ))


def _scope_section(scope_code, title, snapshot):
    rows = snapshot["links"][scope_code]
    summary = snapshot["summaries"].get(scope_code, {})
    slug = "equity" if scope_code.endswith("EQUITY") else "futures"
    children = [
        _leaf(RenderNodeTypeV2.TITLE, f"control.v3.{slug}.title", title, level="SECTION"),
        _leaf(RenderNodeTypeV2.SUBTITLE, f"control.v3.{slug}.summary",
              f"Закрыто: {int(summary.get('closed_total') or 0)} · за час: {int(summary.get('closed_hour') or 0)}"),
    ]
    if rows:
        children.append(_links_table(scope_code, rows))
    else:
        children.append(_leaf(RenderNodeTypeV2.TEXT, f"control.v3.{slug}.empty",
                              "Пока нет закрытых сделок этого исследовательского потока"))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, f"control.v3.scope.{slug}", children=tuple(children))


def _branch_plan_section(rows):
    columns = ("Приоритет", "Инструмент", "Стратегия", "Точная ветка", "Накоплено", "Статус")
    header = RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, "control.v3.plan.header", children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"control.v3.plan.header.{index}", label)
        for index, label in enumerate(columns, start=1)))
    body = []
    status_names = {
        "ACTIVE": "Накапливается", "ACTIVE_SPLIT_REGIME": "Разделяется по режимам",
        "WAITING_CONTEXT_DEFINITION": "Нужно определить контекст", "READY_FOR_OOS": "Готово к OOS",
        "WAITING_CONTEXT": "Нужно определить контекст", "STALE_CONTRACT": "Устаревший контракт",
        "BLOCKED_DIRECTION": "Запрещено направлением",
    }
    for index, item in enumerate(rows, start=1):
        operator_status = str(item.get("operator_status") or item.get("status_code") or "WAITING")
        context = " · ".join((
            {"LONG":"Покупка", "SHORT":"Продажа"}.get(str(item["side_code"]).upper(), str(item["side_code"])),
            str(item.get("session_code") or "Сессия не определена").replace("_", " "),
            _regime_ru(item.get("regime_code")), _exit_ru(item.get("exit_rule")),
        ))
        body.append(RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, f"control.v3.plan.row.{index}",
            state=RenderNodeStateV2(status_code="BLOCKED" if operator_status in {"STALE_CONTRACT", "BLOCKED_DIRECTION"} else "OK" if operator_status == "READY_FOR_OOS" else "WARNING",
                                    source_identity=str(item["strategy_code"]), source_as_of=_utc(item.get("updated_at"))),
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.priority", index),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.symbol", item["symbol"]),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.strategy", _strategy_ru(item["strategy_code"])),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.context", context),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.count",
                      f"{int(item['accumulated_trades'])} / {int(item['target_trades'])}"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.plan.row.{index}.status",
                      status_names.get(operator_status, "Ожидает")),
            )))
    table = RenderNodeV2(RenderNodeTypeV2.TABLE, "control.v3.plan.table", children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, "control.v3.plan.head", children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, "control.v3.plan.body", children=tuple(body)),
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.plan", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.plan.title", "Точные ветки из архива", level="SECTION"),
        _leaf(RenderNodeTypeV2.SUBTITLE, "control.v3.plan.subtitle",
              "Архив задаёт приоритет; свежие сделки подтверждают каждую связку независимо"),
        table,
    ))


def _compact_control_section(snapshot):
    state = snapshot["command_state"]
    refresh_active = int(state.get("refresh_active") or 0)
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.compact_control", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.compact_control.title",
              "Автономный поиск устойчивого преимущества", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "control.v3.compact_control.status",
              "Работает автономно — нажатия не требуются"),
        _command("refresh", "Обновить", "research.request.refresh",
                 "RESEARCH.REQUEST_REFRESH", enabled=refresh_active == 0,
                 rollback_code="RESEARCH.CANCEL_PENDING_REQUEST"),
    ))


def _priority_exact_section(rows):
    columns = ("Инструмент", "Направление", "Прогресс")
    header = RenderNodeV2(RenderNodeTypeV2.TABLE_ROW, "control.v3.exact.header", children=tuple(
        _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"control.v3.exact.header.{index}", label)
        for index, label in enumerate(columns, start=1)))
    body = []
    for index, row in enumerate(rows, start=1):
        trades = int(row.get("closed_trades") or 0)
        direction = {"LONG":"Покупка", "SHORT":"Продажа"}.get(
            str(row.get("side_code")).upper(), str(row.get("side_code")))
        body.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, f"control.v3.exact.row.{index}",
            state=RenderNodeStateV2(
                status_code="OK" if row.get("decision_code") == "READY_FOR_OOS" else "WARNING",
                source_identity="analytics.hierarchical_evidence_v1",
                source_as_of=_utc(row.get("updated_at")),
            ),
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.exact.row.{index}.branch",
                      f"{row.get('symbol_code')} · {str(row.get('timeframe_code')).replace('M', '')} мин"),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.exact.row.{index}.direction", direction),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"control.v3.exact.row.{index}.trades",
                      f"{trades} / {20 if trades < 20 else 80}"),
            ),
        ))
    table = RenderNodeV2(RenderNodeTypeV2.TABLE, "control.v3.exact.table", children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, "control.v3.exact.head", children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, "control.v3.exact.body", children=tuple(body)),
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.exact", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.exact.title",
              "Ближайшие к проверке", level="SECTION"),
        table,
    ))


def _compact_state_section(snapshot, raw_process_status):
    failures = int(snapshot["command_state"].get("failed_24h") or 0)
    failed_process = raw_process_status in {"FAILED", "ERROR", "STALLED", "BLOCKED"}
    if failures or failed_process:
        status, text = "BLOCKED", "Есть ошибка research-процесса — откройте диагностику"
    else:
        status, text = "OK", "Система работает автономно, действий не требуется"
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.state",
        state=RenderNodeStateV2(status_code=status), children=(
            _leaf(RenderNodeTypeV2.TITLE, "control.v3.state.title", "Состояние", level="SECTION"),
            _leaf(RenderNodeTypeV2.TEXT, "control.v3.state.value", text),
        ))


def render_control_compact_v3(snapshot, *, timezone_code="Europe/Moscow", document_id="operator.control.v3"):
    process = snapshot["process"]
    raw_process_status = str(process.get("status_code") or "").upper()
    nearest = snapshot.get("hierarchy_nearest") or {}
    nearest_trades = int(nearest.get("closed_trades") or 0)
    nearest_target = 20 if nearest_trades < 20 else 80
    freshness = snapshot.get("freshness") or ()
    fresh = bool(freshness) and all(
        int(row.get("age_sec") or 0) <= (180 if row.get("timeframe") == "M1" else 420)
        for row in freshness
    )
    cards = RenderNodeV2(RenderNodeTypeV2.GRID, "control.v3.summary", children=(
        _card("mode", "Режим", "Автономный", "Учебный режим: реальных сделок нет", "OK"),
        _card("data", "Данные", "Свежие" if fresh else "Ожидание бара",
              "Семь V5-серий", "OK" if fresh else "WARNING"),
        _card("sample", "Завершено примеров", snapshot["closed_total"], "Только новые сопоставимые данные", "OK"),
        _card("best", "Больше всего примеров", f"{nearest_trades} / {nearest_target}",
              str(nearest.get("symbol_code") or "Нет данных"), "WARNING"),
        _card("ready", "Готово к независимой проверке", int(snapshot["ready_links"]),
              "Только после 80 одинаковых примеров", "OK" if snapshot["ready_links"] else "WARNING"),
    ))
    page = RenderNodeV2(RenderNodeTypeV2.PAGE, "control.v3.page", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.title", "MarketCore", level="PAGE"),
        _leaf(RenderNodeTypeV2.SUBTITLE, "control.v3.subtitle",
              "Поиск устойчивого преимущества · без реальных сделок"),
        RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.overview", children=(cards,)),
        _compact_state_section(snapshot, raw_process_status),
        _priority_exact_section(snapshot.get("hierarchy_top_exact") or ()),
        _multi_asset_section(snapshot.get("asset_branches") or (),
                             snapshot.get("cny_spot_controls") or ()),
        _open_positions_section(snapshot.get("open_position_diagnostics") or ()),
        _compact_control_section(snapshot),
    ))
    root = RenderNodeV2(RenderNodeTypeV2.WORKSPACE, "control.v3.workspace", children=(page,))
    document = RenderDocumentV2(document_id=document_id, root=root, locale_code="ru-RU",
                                fallback_locale_code="ru-RU", generated_at=snapshot["generated_at"],
                                source_as_of=snapshot["generated_at"],
                                timezone_code=timezone_code, quality_code="VERIFIED")
    validate_render_document_v2(document)
    return document
