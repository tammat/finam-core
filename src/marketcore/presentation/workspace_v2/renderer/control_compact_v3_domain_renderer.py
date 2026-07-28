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


def render_control_compact_v3(snapshot, *, timezone_code="Europe/Moscow", document_id="operator.control.v3"):
    process = snapshot["process"]
    process_status = _ru_status(process.get("status_code"))
    process_progress = float(process.get("progress_pct") or 0)
    raw_process_status = str(process.get("status_code") or "").upper()
    process_action = ("Проверить причину и повторить" if raw_process_status in {"FAILED", "ERROR", "STALLED", "BLOCKED"}
                      else "Дождаться завершения" if raw_process_status in {"RUNNING", "ACTIVE", "IN_PROGRESS", "PROCESSING"}
                      else "Дождаться запуска" if raw_process_status in {"PENDING", "QUEUED", "WAITING", "SCHEDULED"}
                      else "Действий не требуется")
    cards = RenderNodeV2(RenderNodeTypeV2.GRID, "control.v3.summary", children=(
        _card("closed", "Закрыто", snapshot["closed_hour"], "За час", "OK" if snapshot["closed_hour"] else "WARNING"),
        _card("sample", "V5 всего", snapshot["closed_total"], "Подтверждённая режимная когорта", "OK" if snapshot["closed_total"] else "WARNING"),
        _card("excluded", "Исключено", snapshot["excluded_closed"], "Закрытия вне чистой методологии", "WARNING" if snapshot["excluded_closed"] else "OK"),
        _card("open", "Открыто Paper", snapshot["open_positions"], "Изолированный research scope", "WARNING" if snapshot["open_positions"] else "OK"),
        _card("ready", "OOS готово", snapshot["ready_links"], f"Цель {snapshot['target_trades']}", "OK" if snapshot["ready_links"] else "WARNING"),
        _card("process", "Процесс", process_status, f"{process_progress:.0f}%", "BLOCKED" if raw_process_status in {"FAILED", "ERROR", "STALLED", "BLOCKED"} else "OK" if process_status == "Готово" else "WARNING"),
        _card("constraint", "Ограничение", snapshot["constraint"], "Свежие данные", "BLOCKED" if snapshot["closed_total"] == 0 else "WARNING"),
        _card("next", "Что делать", process_action if process_action != "Действий не требуется" else snapshot["next_action"], "Автоматически", "OK" if process_status == "Готово" else "WARNING"),
    ))
    process_section = RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.process", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.process.title", "Текущий процесс", level="SECTION"),
        _metric_row("status", "Статус", process_status),
        _metric_row("step", "Этап", str(process.get("current_step") or "Нет данных").replace("_", " ")),
        _metric_row("progress", "Прогресс, %", process_progress),
    ))
    opportunities = RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.opportunities", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.opportunities.title", "Ближе к PASS", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "control.v3.opportunities.value",
              (f"{snapshot['nearest']['symbol']} · {_strategy_ru(snapshot['nearest']['strategy'])} · "
               f"{snapshot['nearest']['accumulated']} из {snapshot['target_trades']}"
               if snapshot["nearest"] else "Свежих связок пока нет")),
    ))
    attention = RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.attention", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.attention.title", "Требует внимания", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "control.v3.attention.value", snapshot["constraint"]),
    ))
    archive = RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.archive", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.archive.title", "Архив и диагностика", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "control.v3.archive.value",
              "Старые данные используются только для диагностики и генерации гипотез, но не для нового PASS"),
    ))
    page = RenderNodeV2(RenderNodeTypeV2.PAGE, "control.v3.page", children=(
        _leaf(RenderNodeTypeV2.TITLE, "control.v3.title", "MarketCore", level="PAGE"),
        _leaf(RenderNodeTypeV2.SUBTITLE, "control.v3.subtitle", "Контроль · чистая статистика · готовность к OOS"),
        RenderNodeV2(RenderNodeTypeV2.SECTION, "control.v3.overview", children=(cards, opportunities, attention)),
        _scope_section("FRESH_V5_CONFIRMED_EQUITY", "Акции", snapshot),
        _scope_section("FRESH_V5_CONFIRMED_FUTURES", "Фьючерсы", snapshot),
        _branch_plan_section(snapshot.get("branch_plan") or ()),
        process_section,
        archive,
    ))
    root = RenderNodeV2(RenderNodeTypeV2.WORKSPACE, "control.v3.workspace", children=(page,))
    document = RenderDocumentV2(document_id=document_id, root=root, locale_code="ru-RU",
                                fallback_locale_code="ru-RU", generated_at=snapshot["generated_at"],
                                source_as_of=snapshot["generated_at"],
                                timezone_code=timezone_code, quality_code="VERIFIED")
    validate_render_document_v2(document)
    return document
