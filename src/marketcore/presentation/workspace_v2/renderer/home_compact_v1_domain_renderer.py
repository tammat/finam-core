from __future__ import annotations

from datetime import timezone
from zoneinfo import ZoneInfo

from marketcore.presentation.render_tree.v2 import (
    ActionKindV2, RenderActionV2, RenderContentV2, RenderDocumentV2,
    RenderNodeStateV2, RenderNodeTypeV2, RenderNodeV2, validate_render_document_v2,
)


def _leaf(kind, node_id, value=None, *, level=None, status=None):
    kwargs = {"content": RenderContentV2(value=value, level_code=level)}
    if status:
        kwargs["state"] = RenderNodeStateV2(status_code=status)
    return RenderNodeV2(kind, node_id, **kwargs)


def _row(code, label, value, *, status="OK", source=None, source_as_of=None):
    if source_as_of is not None and source_as_of.tzinfo is not None:
        source_as_of = source_as_of.astimezone(timezone.utc)
    return RenderNodeV2(
        RenderNodeTypeV2.METRIC_ROW,
        f"home.compact.{code}",
        state=RenderNodeStateV2(
            status_code=status,
            source_identity=source if source_as_of is not None else None,
            source_as_of=source_as_of,
        ),
        children=(
            _leaf(RenderNodeTypeV2.METRIC_LABEL, f"home.compact.{code}.label", label),
            _leaf(RenderNodeTypeV2.METRIC_VALUE, f"home.compact.{code}.value", value),
        ),
    )


def _age_text(seconds):
    if seconds is None:
        return "время обновления неизвестно"
    seconds = max(0, int(seconds))
    if seconds < 60:
        return f"обновлены {seconds} сек. назад"
    return f"обновлены {seconds // 60} мин. назад"


def _instrument_name(row):
    symbol = str(row.get("symbol_code") or row.get("symbol") or "")
    ticker = symbol.split("@", 1)[0]
    fallback = {
        "NVTK": "Новатэк", "SBERP": "Сбербанк-п", "PLZL": "Полюс",
        "OZON": "Озон", "SFIN": "ЭсЭфАй", "T": "Т-Технологии",
        "X5": "Корпоративный центр ИКС 5", "EUTR": "ЕвроТранс",
        "CNYRUBF": "Юань", "USDRUBF": "Доллар", "GDU6": "Золото",
    }
    name = str(row.get("instrument_name") or fallback.get(ticker) or ticker)
    return f"{name} ({ticker})" if name != ticker else ticker


def _signed_metric(value, *, available=True):
    if not available or value is None:
        return "нет данных"
    return f"{float(value):+.2f}".replace(".", ",")


def _pf_text(row):
    if not row.get("profit_factor_observable"):
        return "нет данных"
    return f"{float(row.get('profit_factor') or 0):.2f}".replace(".", ",")


def _now_section(snapshot):
    freshness = snapshot.get("freshness") or ()
    worst = max(freshness, key=lambda row: int(row.get("age_sec") or 0), default={})
    summary = snapshot.get("data_quality_summary") or {}
    ready = int(summary.get("ready") or 0)
    attention = int(summary.get("attention") or 0)
    outside = int(summary.get("out_of_session") or 0)
    data_ok = bool(freshness) and attention == 0
    quality_text = f"свежие {ready} · задержка {attention} · вне сессии {outside}"
    metrics = RenderNodeV2(RenderNodeTypeV2.METRIC_LIST, "home.compact.now.metrics", children=(
        _row("mode", "Система", "Собирает примеры автоматически"),
        _row("data", "Данные", quality_text,
             status="OK" if data_ok else "WARNING",
             source="market_bars", source_as_of=worst.get("latest_bar")),
        _row("safety", "Реальные сделки", "Выключены"),
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "home.compact.now", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.now.title", "Сейчас", level="SECTION"),
        metrics,
    ))


def _progress_section(snapshot):
    children = [
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.progress.title", "Прогресс", level="SECTION")
    ]
    rows = list(snapshot.get("hierarchy_top_exact") or ())[:5]
    universe = snapshot.get("universe_summary") or {}
    children.append(_row(
        "universe",
        "Охват",
        f"активно {int(universe.get('active_instruments') or 0)} · "
        f"сделки есть у {int(universe.get('instruments_with_closed_v5') or 0)} · "
        f"V5 сегодня {int(universe.get('closed_v5_today') or 0)} · "
        f"на экране топ-{len(rows)}",
        source="runtime_active_universe",
        source_as_of=snapshot.get("generated_at"),
    ))
    direction = {"LONG": "покупка", "SHORT": "продажа"}
    for index, row in enumerate(rows, start=1):
        count = int(row.get("closed_trades") or 0)
        target = 20 if count < 20 else 80
        side = direction.get(str(row.get("side_code") or "").upper(), "наблюдение")
        children.append(_row(
            f"progress.{index}",
            f"{_instrument_name(row)} · {side}",
            f"{count} из {target} · P&L net {_signed_metric(row.get('net_pnl'))} · "
            f"P&L R {_signed_metric(row.get('net_pnl_r'), available=row.get('r_observable'))} · "
            f"Exp/R {_signed_metric(row.get('expectancy_r'), available=row.get('r_observable'))} · "
            f"PF {_pf_text(row)}",
            status="OK" if count >= target else "WARNING",
            source="analytics.hierarchical_evidence_v1",
            source_as_of=row.get("updated_at"),
        ))
    assets = {}
    for row in snapshot.get("asset_branches") or ():
        asset = str(row.get("asset_code"))
        assets.setdefault(asset, 0)
        assets[asset] += int(row.get("closed_trades") or 0)
    names = {"USD": "Доллар", "GOLD": "Золото", "CNY": "Юань"}
    for index, asset in enumerate(("USD", "GOLD", "CNY"), start=1):
        count = assets.get(asset, 0)
        children.append(_row(
            f"asset.{index}", names[asset],
            (
                "завершённых примеров: 0 · ожидает первый допустимый сигнал"
                if count == 0 else f"завершено примеров: {count}"
            ),
            status="WARNING",
            source="analytics.v5_asset_branch_policy_v1",
        ))
    if not rows:
        children.append(_row("progress.empty", "Примеры", "Пока нет завершённых" ,status="WARNING"))
    title, *metrics = children
    metric_list = RenderNodeV2(
        RenderNodeTypeV2.METRIC_LIST, "home.compact.progress.metrics", children=tuple(metrics)
    )
    return RenderNodeV2(
        RenderNodeTypeV2.SECTION, "home.compact.progress", children=(title, metric_list)
    )


def _holding_text(seconds, active=False):
    if seconds is None:
        return "идёт" if active else "—"
    seconds = max(0, int(seconds))
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes = remainder // 60
    if days:
        value = f"{days} д {hours} ч"
    elif hours:
        value = f"{hours} ч {minutes} мин"
    else:
        value = f"{minutes} мин"
    return f"{value} · идёт" if active else value


def _exit_reason_text(reason, active=False):
    if active:
        return "позиция открыта"
    labels = {
        "time_exit": "лимит времени", "TIME_EXIT": "лимит времени",
        "stop_loss_long": "стоп-лосс", "stop_loss_short": "стоп-лосс",
        "STOP": "стоп-лосс", "take_profit_long": "тейк-профит",
        "take_profit_short": "тейк-профит", "TAKE": "тейк-профит",
        "signal_exit": "обратный сигнал", "manual": "закрыта вручную",
        "regime_invalidation_long": "смена режима", "regime_invalidation_short": "смена режима",
        "stall_exit_long": "выход из-за отсутствия движения",
        "stall_exit_short": "выход из-за отсутствия движения",
    }
    return labels.get(str(reason or ""), str(reason or "не указана").replace("_", " "))


def _entry_signal_text(signal):
    labels = {
        "MEAN_REVERSION_EQUITY": "возврат к среднему",
        "VOLATILITY_BREAKOUT_EQUITY": "пробой волатильности",
        "BR_CONSERVATIVE_BREAKOUT": "подтверждённый пробой",
        "NG_CONSERVATIVE_BREAKOUT_M1": "подтверждённый пробой",
        "CNY_REGIME_FUTURES": "ретест уровня по восходящему тренду",
        "USD_REGIME_FUTURES": "ретест уровня по подтверждённому тренду",
        "GOLD_TREND_BREAKOUT": "пробой по направлению тренда",
        "SWING_MEAN_REVERSION": "Swing: возврат к среднему",
        "REGIME_MOMENTUM": "Swing: импульс режима",
        "META_BREAKOUT": "Swing: фильтрованный пробой",
    }
    return labels.get(str(signal or ""), str(signal or "не указан").replace("_", " ").lower())


def _recent_trades_section(snapshot, timezone_code, *, futures):
    code = "futures" if futures else "equities"
    title = "Последние сделки · Фьючерсы" if futures else "Последние сделки · Акции"
    headers = ("Инструмент", "Направление", "Сигнал входа", "Время", "Вход", "Выход", "Удержание", "Причина закрытия", "Статус", "Net P&L, ₽")
    header = RenderNodeV2(
        RenderNodeTypeV2.TABLE_ROW, f"home.compact.trades.{code}.header",
        children=tuple(
            _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"home.compact.trades.{code}.header.{i}", label)
            for i, label in enumerate(headers)
        ),
    )
    rows = []
    local_tz = ZoneInfo(timezone_code)
    items = [item for item in (snapshot.get("recent_trade_events") or ())
             if bool(item.get("is_futures")) == futures]
    for index, item in enumerate(items, start=1):
        event_ts = item.get("event_ts")
        time_text = event_ts.astimezone(local_tz).strftime("%H:%M:%S") if event_ts else "—"
        status = "Закрыта" if item.get("event_status") == "CLOSED" else "Активна"
        direction = "LONG" if item.get("direction") == "LONG" else "SHORT"
        pnl = item.get("net_pnl")
        pnl_status = "PROFIT" if pnl is not None and float(pnl) > 0 else (
            "LOSS" if pnl is not None and float(pnl) < 0 else None
        )
        def number(value):
            return "—" if value is None else f"{float(value):.4f}".rstrip("0").rstrip(".").replace(".", ",")
        exit_text = (
            (f"{float(pnl):+.2f} ₽".replace(".", ",") if pnl is not None else "—")
            if status == "Активна" else number(item.get("exit_price"))
        )
        rows.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, f"home.compact.trades.{code}.row.{index}",
            state=RenderNodeStateV2(status_code="ACTIVE") if status == "Активна" else None,
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.symbol", _instrument_name(item)),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.direction", direction),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.signal", _entry_signal_text(item.get("entry_signal"))),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.time", time_text),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.entry", number(item.get("entry_price"))),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.exit", exit_text, status=pnl_status if status == "Активна" else None),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.holding", _holding_text(item.get("holding_seconds"), status == "Активна")),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.reason", _exit_reason_text(item.get("exit_reason"), status == "Активна")),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.trade_state", status),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.pnl", number(pnl), status=pnl_status),
            ),
        ))
    table = RenderNodeV2(RenderNodeTypeV2.TABLE, f"home.compact.trades.{code}.table", children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, f"home.compact.trades.{code}.head", children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, f"home.compact.trades.{code}.body", children=tuple(rows)),
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, f"home.compact.trades.{code}", children=(
        _leaf(RenderNodeTypeV2.TITLE, f"home.compact.trades.{code}.title", title, level="SECTION"),
        table,
    ))


def _attention_section(snapshot):
    state = snapshot.get("command_state") or {}
    refresh_active = int(state.get("refresh_active") or 0)
    process_code = str((snapshot.get("process") or {}).get("status_code") or "").upper()
    process_failed = process_code in {"FAILED", "ERROR", "STALLED", "BLOCKED"}
    freshness = snapshot.get("freshness") or ()
    blocking_quality_codes = {"STALE", "GAP", "NO_COMPLETED_BARS", "COST_SPEC_STALE"}
    data_stale = any(row.get("quality_code") in blocking_quality_codes for row in freshness)
    if process_failed:
        message, status = "Текущий поиск остановился. Откройте диагностику.", "BLOCKED"
    elif data_stale:
        message, status = "Данные задерживаются. Система обновит их автоматически.", "WARNING"
    else:
        message, status = "Всё работает автоматически. Ничего нажимать не нужно.", "OK"
    refresh = RenderNodeV2(
        RenderNodeTypeV2.ACTION,
        "home.compact.refresh",
        content=RenderContentV2(value="Обновить"),
        action=RenderActionV2(
            "research.request.refresh", ActionKindV2.COMMAND,
            command_code="RESEARCH.REQUEST_REFRESH",
            policy_class="RESEARCH_MAINTENANCE",
            enabled=refresh_active == 0,
            blocked_reason_code=(None if refresh_active == 0 else "RESEARCH_COMMAND_ALREADY_ACTIVE"),
            reversible=True,
            rollback_code="RESEARCH.CANCEL_PENDING_REQUEST",
            idempotency_key="client.request",
        ),
    )
    return RenderNodeV2(
        RenderNodeTypeV2.SECTION, "home.compact.attention",
        state=RenderNodeStateV2(status_code=status),
        children=(
            _leaf(RenderNodeTypeV2.TITLE, "home.compact.attention.title", "Нужно внимание", level="SECTION"),
            _leaf(RenderNodeTypeV2.TEXT, "home.compact.attention.message", message),
            refresh,
        ),
    )


def render_home_compact_v1(snapshot, *, timezone_code="Europe/Moscow"):
    page = RenderNodeV2(RenderNodeTypeV2.PAGE, "home.compact.page", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.title", "MarketCore", level="PAGE"),
        _leaf(RenderNodeTypeV2.SUBTITLE, "home.compact.subtitle",
              "Поиск преимущества · без реальных сделок"),
        _now_section(snapshot),
        _progress_section(snapshot),
        _recent_trades_section(snapshot, timezone_code, futures=False),
        _recent_trades_section(snapshot, timezone_code, futures=True),
        _attention_section(snapshot),
    ))
    document = RenderDocumentV2(
        document_id="operator.home.v2",
        root=RenderNodeV2(RenderNodeTypeV2.WORKSPACE, "home.compact.workspace", children=(page,)),
        locale_code="ru-RU", fallback_locale_code="ru-RU",
        generated_at=snapshot["generated_at"], source_as_of=snapshot["generated_at"],
        timezone_code=timezone_code, quality_code="VERIFIED",
    )
    validate_render_document_v2(document)
    return document
