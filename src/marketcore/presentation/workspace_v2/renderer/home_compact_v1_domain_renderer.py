from __future__ import annotations

from datetime import datetime, timezone
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
    session = snapshot.get("session_status") or {}
    calendar_closed = session.get("reason") == "exchange_calendar_closed"
    if calendar_closed:
        next_open = session.get("next_open")
        next_text = next_open.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m %H:%M") if next_open else "уточняется"
        quality_text = f"биржа закрыта по календарю · следующая сессия {next_text} МСК"
    else:
        quality_text = f"свежие {ready} · задержка {attention} · вне сессии {outside}"
    promotion = snapshot.get("promotion_summary") or {}
    promoted = int(promotion.get("promoted_oos") or 0)
    admitted = int(promotion.get("paper_admitted") or 0)
    if promoted > 0 and admitted > 0:
        paper_text = f"Допущено связок: {admitted} · подтверждено OOS: {promoted}"
        paper_status = "OK"
    else:
        paper_text = (
            "Доказанных связок: 0 · Paper в экспериментальном режиме "
            "с минимальным размером · REAL выключен"
        )
        paper_status = "WARNING"
    event = snapshot.get("market_event_risk") or {}
    shock = snapshot.get("market_shock_gate") or {}
    risk_level = str(event.get("risk_level") or "NORMAL").upper()
    risk_label = {
        "SHOCK": "Рыночный шок — новые входы только Shadow",
        "ELEVATED": "Повышенный риск — новые входы только Shadow",
        "RECOVERY": "Стабилизация — проверяются гэп, ATR, спред и объём",
        "NORMAL": "Нормальный режим",
    }.get(risk_level, "Состояние риска уточняется")
    if event.get("title_ru"):
        risk_label = f"{event.get('title_ru')} · {risk_label}"
    if shock.get("reason_code"):
        shock_reason = {
            "MARKET_EVENT_SHOCK": "новые входы переведены в Shadow",
            "MARKET_EVENT_ELEVATED": "новые входы переведены в Shadow",
            "RECOVERY_POLICY_NOT_VALIDATED": "восстановление ещё не доказано",
            "MARKET_CONTEXT_STALE": "рыночный контекст устарел",
            "WAIT_COMPLETED_M15": "ожидается завершённая M15",
        }.get(str(shock.get("reason_code")), "решение защитного фильтра")
        risk_label += f" · {shock_reason}"
    readiness = snapshot.get("monday_readiness") or {}
    resources = snapshot.get("research_resource_gate") or {}
    readiness_label = {
        "CALENDAR_CLOSED": "биржа закрыта по календарю",
        "SHADOW_ONLY": "только Shadow",
        "WAIT": "ожидание прогрева M15",
        "BLOCK": "входы заблокированы",
        "RECOVERY_CHECK": "проверка восстановления по каждому инструменту",
        "PAPER_READY": "базовый Paper-допуск готов",
    }.get(str(readiness.get("verdict_code") or ""), "ещё не рассчитана")
    if readiness.get("reason_code"):
        readiness_reason = {
            "EXCHANGE_CALENDAR_CLOSED": "следующая проверка перед открытием",
            "MARKET_EVENT_SHOCK": "новые входы только Shadow",
            "MARKET_EVENT_ELEVATED": "новые входы только Shadow",
            "RECOVERY_POLICY_NOT_VALIDATED": "восстановление не подтверждено replay",
            "WAIT_COMPLETED_M15": "ожидается первая завершённая M15",
            "MARKET_CONTEXT_STALE": "ожидаются свежие MX и RVI",
            "ACTIVE_POSITIONS_PRESENT": "контролируются открытые позиции",
            "OOS_NOT_READY": "копится независимая выборка",
        }.get(str(readiness.get("reason_code")), "требуется автоматическая повторная проверка")
        readiness_label += f" · {readiness_reason}"
    metrics = RenderNodeV2(RenderNodeTypeV2.METRIC_LIST, "home.compact.now.metrics", children=(
        _row("mode", "Система", "Собирает примеры автоматически"),
        _row("data", "Данные", quality_text,
             status="OK" if data_ok else "WARNING",
             source="market_bars", source_as_of=worst.get("latest_bar")),
        _row("paper", "Paper", paper_text, status=paper_status,
             source="analytics.edge_oos_result_v1",
             source_as_of=snapshot.get("generated_at")),
        _row("event-risk", "Риск событий", risk_label,
             status="WARNING" if risk_level in {"SHOCK", "ELEVATED", "RECOVERY"} else "OK",
             source="analytics.market_event_risk_v1",
             source_as_of=event.get("updated_at") or snapshot.get("generated_at")),
        _row("monday-readiness", "Готовность сессии", readiness_label,
             status="OK" if readiness.get("verdict_code") in {"PAPER_READY", "CALENDAR_CLOSED"} else "WARNING",
             source="analytics.monday_readiness_snapshot_v1",
             source_as_of=readiness.get("evaluated_at") or snapshot.get("generated_at")),
        _row("research-resources", "Ресурсы исследований",
             (f"тяжёлые расчёты отложены: {int(resources.get('deferred_hour') or 0)} за час · "
              f"последний: {resources.get('last_deferred_job') or 'нет'}"
              if int(resources.get("deferred_hour") or 0) else
              "нагрузка допустима · тяжёлые расчёты выполняются по очереди"),
             status="WARNING" if int(resources.get("deferred_hour") or 0) else "OK",
             source="analytics.research_resource_gate_audit_v1",
             source_as_of=resources.get("evaluated_at") or snapshot.get("generated_at")),
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
        assets[asset] = max(assets[asset], int(row.get("closed_trades") or 0))
    names = {"USD": "Доллар", "GOLD": "Золото", "CNY": "Юань"}
    for index, asset in enumerate(("USD", "GOLD", "CNY"), start=1):
        count = assets.get(asset, 0)
        if count == 0:
            progress_text = (
                "0 из 20 · вне Top‑5: нет допустимых закрытых V5-сделок · "
                "следующий шаг: устранить блокировки и продолжать Paper"
            )
        elif count < 20:
            progress_text = (
                f"{count} из 20 · вне Top‑5: выборка пока мала · "
                "следующий шаг: продолжать Paper на новых сигналах"
            )
        elif count < 80:
            progress_text = (
                f"{count} из 80 · базовая выборка собрана · следующий шаг: накопление до OOS"
            )
        else:
            progress_text = f"{count} из 80 · выборка готова к OOS-допуску"
        children.append(_row(
            f"asset.{index}", names[asset],
            progress_text,
            status="OK" if count >= 80 else "WARNING",
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


def _workflow_section(snapshot):
    """Explain the autonomous Paper -> Shadow -> OOS workflow on one screen."""
    evidence = snapshot.get("v5_oos_evidence") or {}
    readiness = snapshot.get("monday_readiness") or {}
    shadow_rows = list(snapshot.get("shadow_dynamics") or ())
    waiting = int(evidence.get("waiting_admissions") or 0)
    collecting = int(evidence.get("collecting_runs") or 0)
    passed = int(evidence.get("passed_runs") or 0)
    verdict = str(readiness.get("verdict_code") or "")
    reason = str(readiness.get("reason_code") or "")

    reason_ru = {
        "EXCHANGE_CALENDAR_CLOSED": "биржа закрыта по календарю",
        "MARKET_EVENT_SHOCK": "действует событийный шок",
        "MARKET_EVENT_ELEVATED": "событийный риск повышен",
        "RECOVERY_POLICY_NOT_VALIDATED": "правила восстановления ещё не доказаны",
        "WAIT_COMPLETED_M15": "ожидается завершённая свеча M15",
        "MARKET_CONTEXT_STALE": "индекс или RVI ещё не обновились",
        "ACTIVE_POSITIONS_PRESENT": "есть открытые Paper-позиции",
        "OOS_NOT_READY": "не накоплена независимая OOS-выборка",
    }.get(reason, reason.lower().replace("_", " ") if reason else "ограничений нет")

    if verdict == "CALENDAR_CLOSED":
        next_step = "В понедельник система сама проверит календарь, MX/RVI и первую завершённую M15"
    elif verdict in {"SHADOW_ONLY", "BLOCK", "RECOVERY_CHECK"}:
        next_step = f"Paper-входы не расширять: {reason_ru}; продолжать Shadow"
    elif verdict == "WAIT":
        next_step = f"Подождать автоматически: {reason_ru}"
    elif verdict == "PAPER_READY":
        next_step = "Собирать Paper минимальным размером; REAL остаётся выключен"
    else:
        next_step = "Дождаться ближайшего автоматического расчёта готовности"

    rows = (
        _row("workflow.paper", "1. Paper",
             f"текущая политика собирает виртуальные исполнения по реальному рынку; "
             f"закрытых сделок в доказательной выборке: {int(evidence.get('paper_trades') or 0)}"),
        _row("workflow.shadow", "2. Shadow",
             f"параллельно проверяются альтернативы без заявок брокеру; "
             f"вариантов с результатами на экране: {len(shadow_rows)}",
             status="OK" if shadow_rows else "WARNING"),
        _row("workflow.oos", "3. V5 OOS",
             f"ожидают свежую выборку: {waiting} · проходят независимую проверку: {collecting} · "
             f"подтверждено: {passed}", status="OK" if passed else "WARNING"),
        _row("workflow.next", "Следующий шаг", next_step,
             status="OK" if verdict == "PAPER_READY" else "WARNING",
             source="analytics.monday_readiness_snapshot_v1",
             source_as_of=readiness.get("evaluated_at") or snapshot.get("generated_at")),
        _row("workflow.real", "Реальная торговля", "выключена до OOS PASS и отдельного допуска"),
    )
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "home.compact.workflow", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.workflow.title",
              "Путь к доказанному edge", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "home.compact.workflow.help",
              "Система продвигает кандидата автоматически только после проверки на новых данных."),
        RenderNodeV2(RenderNodeTypeV2.METRIC_LIST,
                     "home.compact.workflow.metrics", children=rows),
    ))


def _lightweight_statistics_section(snapshot):
    stats=snapshot.get("lightweight_statistics") or {}
    groups=int(stats.get("groups_total") or 0)
    hold_seconds=int(stats.get("median_hold_seconds") or 0)
    hold_text=_holding_text(hold_seconds) if hold_seconds else "нет данных"
    if not stats:
        rows=(_row("statistics.empty","Статистический слой",
                   "первый ночной расчёт ещё не завершён",status="WARNING"),)
    else:
        rows=(
            _row("statistics.bootstrap","Block bootstrap",
                 f"положительная вероятность ≥80%: {int(stats.get('bootstrap_positive') or 0)} из {groups}",
                 status="OK" if int(stats.get("bootstrap_positive") or 0) else "WARNING"),
            _row("statistics.mde","Необходимая выборка",
                 f"достигли MDE: {int(stats.get('mde_reached') or 0)} · "
                 f"медианно осталось сделок: {int(stats.get('median_mde_remaining') or 0)}"),
            _row("statistics.concentration","Концентрация прибыли",
                 f"устойчивы без одной сделки/дня: {int(stats.get('concentration_pass') or 0)} из {groups}"),
            _row("statistics.survival","Удержание и TIME_EXIT",
                 f"медианное удержание: {hold_text} · survival хранится по горизонтам 15–480 минут"),
            _row("statistics.cusum","Деградация CUSUM",
                 f"предупреждений: {int(stats.get('degradation_alerts') or 0)}",
                 status="WARNING" if int(stats.get("degradation_alerts") or 0) else "OK"),
            _row("statistics.next","Дорогие проверки",
                 f"готовы к CPCV/PBO/DSR: {int(stats.get('ready_for_expensive_gates') or 0)}",
                 status="OK" if int(stats.get("ready_for_expensive_gates") or 0) else "WARNING"),
        )
    return RenderNodeV2(RenderNodeTypeV2.SECTION,"home.compact.statistics",children=(
        _leaf(RenderNodeTypeV2.TITLE,"home.compact.statistics.title",
              "Статистическая доказательность",level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT,"home.compact.statistics.help",
              "Лёгкие проверки выполняются первыми; тяжёлые CPCV/PBO получают только финалисты."),
        RenderNodeV2(RenderNodeTypeV2.METRIC_LIST,"home.compact.statistics.metrics",children=rows),
    ))


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
        "hard_max_hold_exit": "аварийный лимит удержания",
        "paper_session_end_exit": "аварийное закрытие перед концом сессии",
        "hard_max_hold_trend_extension": "удержание продлено по подтверждённому тренду",
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
        opened_at = item.get("opened_at") or event_ts
        carryover = bool(
            opened_at
            and opened_at.astimezone(local_tz).date() < datetime.now(local_tz).date()
        )
        time_text = (
            opened_at.astimezone(local_tz).strftime(
                "%d.%m %H:%M" if carryover else "%H:%M:%S"
            )
            if opened_at else "—"
        )
        status = "Закрыта" if item.get("event_status") == "CLOSED" else "Активна"
        status_text = (
            "Активна · перенос" if status == "Активна" and carryover else status
        )
        direction = "LONG" if item.get("direction") == "LONG" else "SHORT"
        pnl = item.get("net_pnl")
        pnl_status = "PROFIT" if pnl is not None and float(pnl) > 0 else (
            "LOSS" if pnl is not None and float(pnl) < 0 else None
        )
        def number(value):
            return "—" if value is None else f"{float(value):.4f}".rstrip("0").rstrip(".").replace(".", ",")
        exit_text = (
            (f"≈ {float(pnl):+.2f} ₽".replace(".", ",") if pnl is not None else "—")
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
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.trade_state", status_text),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.trades.{code}.row.{index}.pnl", number(pnl), status=pnl_status),
            ),
        ))
    totals = (
        ("realized", "Закрытые сегодня",
         next((item.get("daily_realized_net_pnl") for item in items
               if item.get("daily_realized_net_pnl") is not None), None)),
        ("unrealized", "Открытые сейчас · предварительно",
         next((item.get("active_unrealized_net_pnl") for item in items
               if item.get("active_unrealized_net_pnl") is not None), None)),
    )
    for total_code, total_label, total_value in totals:
        total_status = (
            "PROFIT" if total_value is not None and float(total_value) > 0
            else "LOSS" if total_value is not None and float(total_value) < 0 else None
        )
        total_text = (
            "—" if total_value is None
            else f"{float(total_value):+.2f}".replace(".", ",")
        )
        rows.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, f"home.compact.trades.{code}.{total_code}_total",
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL,
                      f"home.compact.trades.{code}.{total_code}_total.label", total_label),
                *tuple(_leaf(RenderNodeTypeV2.TABLE_CELL,
                             f"home.compact.trades.{code}.{total_code}_total.blank.{i}", "")
                       for i in range(8)),
                _leaf(RenderNodeTypeV2.TABLE_CELL,
                      f"home.compact.trades.{code}.{total_code}_total.pnl",
                      total_text, status=total_status),
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


def _shadow_dynamics_section(snapshot):
    headers = (
        "Инструмент", "Направление", "Shadow-вариант", "Сопоставимых пар",
        "Exp после издержек, R", "Placebo, R", "Преимущество, R",
        "Нижняя граница, R", "Вердикт",
    )
    header = RenderNodeV2(
        RenderNodeTypeV2.TABLE_ROW, "home.compact.shadow.header",
        children=tuple(
            _leaf(RenderNodeTypeV2.TABLE_HEADER_CELL, f"home.compact.shadow.header.{i}", label)
            for i, label in enumerate(headers)
        ),
    )
    items = tuple(snapshot.get("shadow_dynamics") or ())
    raw_items = tuple(snapshot.get("raw_shadow_dynamics") or ())
    stream_latest = next(
        (item.get("stream_latest_result_ts") for item in raw_items
         if item.get("stream_latest_result_ts")),
        None,
    )
    stream_freshness = (
        stream_latest.strftime("%d.%m %H:%M") if stream_latest else "нет результатов"
    )
    rows = []
    for index, item in enumerate(items, start=1):
        def metric(value):
            return "—" if value is None else f"{float(value):+.2f}".replace(".", ",")
        pairs = int(item.get("pairs") or 0)
        lower = item.get("delta_lower_bound_r")
        passed = (
            pairs >= 10 and bool(item.get("placebo_passed"))
            and lower is not None and float(lower) > 0
        )
        verdict = (
            "Предварительно лучше placebo" if passed else
            "Мало данных" if pairs < 10 else
            "Преимущество не подтверждено"
        )
        rows.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, f"home.compact.shadow.row.{index}",
            state=RenderNodeStateV2(status_code="OK" if passed else "WARNING"),
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.symbol", _instrument_name(item)),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.side", str(item.get("side_code") or "—")),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.candidate", str(item.get("candidate_code") or "—")),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.pairs", str(pairs)),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.exp", metric(item.get("candidate_expectancy_r"))),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.placebo", metric(item.get("placebo_expectancy_r"))),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.delta", metric(item.get("delta_expectancy_r"))),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.lower", metric(lower)),
                _leaf(RenderNodeTypeV2.TABLE_CELL, f"home.compact.shadow.row.{index}.verdict", verdict),
            ),
        ))
    if not rows:
        rows.append(RenderNodeV2(
            RenderNodeTypeV2.TABLE_ROW, "home.compact.shadow.empty",
            children=(
                _leaf(RenderNodeTypeV2.TABLE_CELL, "home.compact.shadow.empty.text",
                      "Завершённых Shadow-наблюдений пока нет"),
                *tuple(_leaf(RenderNodeTypeV2.TABLE_CELL,
                             f"home.compact.shadow.empty.blank.{i}", "") for i in range(8)),
            ),
        ))
    table = RenderNodeV2(RenderNodeTypeV2.TABLE, "home.compact.shadow.table", children=(
        RenderNodeV2(RenderNodeTypeV2.TABLE_HEAD, "home.compact.shadow.head", children=(header,)),
        RenderNodeV2(RenderNodeTypeV2.TABLE_BODY, "home.compact.shadow.body", children=tuple(rows)),
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "home.compact.shadow", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.shadow.title",
              "Research Shadow · сопоставимая V5-оценка (не OOS)", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "home.compact.shadow.help",
              f"Последний завершённый результат во всём Shadow-потоке: {stream_freshness}. "
              "Главная таблица использует дедуплицированные пары одинаковых сигналов, "
              "учитывает издержки и сравнивает вариант с placebo. Кандидат выбирается "
              "по нижней границе преимущества, а не по удачному последнему отрезку. "
              "Это ещё не OOS и не разрешение Paper; заявки брокеру не отправляются."),
        table,
        _raw_shadow_diagnostic(snapshot),
    ))


def _raw_shadow_diagnostic(snapshot):
    items = tuple(snapshot.get("raw_shadow_dynamics") or ())[:8]
    children = [
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.shadow.raw.title",
              "Сырая динамика последних наблюдений — только диагностика", level="CARD"),
        _leaf(RenderNodeTypeV2.TEXT, "home.compact.shadow.raw.warning",
              "Не используется для выбора кандидата и продвижения в Paper."),
    ]
    for index, item in enumerate(items, start=1):
        recent = item.get("recent_expectancy_r")
        previous = item.get("previous_expectancy_r")
        delta = None if recent is None or previous is None else float(recent) - float(previous)
        value = (
            f"{_instrument_name(item)} · {item.get('side_code')} · {item.get('candidate_code')} · "
            f"n={int(item.get('evaluated') or 0)} · последние 20 "
            f"{_signed_metric(recent, available=recent is not None)} · изменение "
            f"{_signed_metric(delta, available=delta is not None)}"
        )
        children.append(_leaf(RenderNodeTypeV2.TEXT, f"home.compact.shadow.raw.{index}", value))
    return RenderNodeV2(RenderNodeTypeV2.CARD, "home.compact.shadow.raw", children=tuple(children))


def _attention_section(snapshot):
    state = snapshot.get("command_state") or {}
    refresh_active = int(state.get("refresh_active") or 0)
    process_code = str((snapshot.get("process") or {}).get("status_code") or "").upper()
    process_failed = process_code in {"FAILED", "ERROR", "STALLED", "BLOCKED"}
    freshness = snapshot.get("freshness") or ()
    blocking_quality_codes = {"STALE", "GAP", "NO_COMPLETED_BARS", "COST_SPEC_STALE"}
    data_stale = any(row.get("quality_code") in blocking_quality_codes for row in freshness)
    session = snapshot.get("session_status") or {}
    if session.get("reason") == "exchange_calendar_closed":
        next_open = session.get("next_open")
        next_text = next_open.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m %H:%M") if next_open else "уточняется"
        message, status = f"Биржа закрыта по календарю. Следующая сессия: {next_text} МСК.", "OK"
    elif process_failed:
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


def _optimizer_section(snapshot):
    cards = []
    check_labels = {
        "parameter_plateau": "устойчивость соседних параметров",
        "positive_expectancy": "положительное матожидание",
        "profit_factor": "profit factor",
        "drawdown": "допустимая просадка",
        "enough_pairs": "достаточно независимых наблюдений",
        "beats_current": "лучше текущего Paper",
    }
    reason_labels = {
        "requires paired trades>=60": "нужно не менее 60 независимых пар",
        "requires purged OOS trades>=15": "нужно не менее 15 очищенных OOS-наблюдений",
    }
    workflow_labels = {
        "SHADOW_ACCUMULATION": "Shadow: накопление статистики",
        "EXPENSIVE_GATES_PENDING": "дорогие проверки ещё не пройдены",
        "EXPENSIVE_GATES_FAILED": "дорогие проверки не пройдены — остаётся Shadow",
        "V5_OOS_COLLECTING": "V5 OOS: собираются только будущие наблюдения",
        "V5_OOS_FAILED": "V5 OOS не пройден — остаётся Shadow",
        "V5_OOS_PASS": "V5 OOS пройден — готов минимальный Paper",
        "PAPER_MINIMAL_ACTIVE": "минимальный Paper активен",
        "PAPER_MONITOR": "Paper: наблюдение динамики",
        "PAPER_CONTINUE": "Paper подтверждён, наблюдение продолжается",
        "ROLLED_BACK": "Paper автоматически откачен",
        "REJECTED": "кандидат отклонён",
    }
    for index, item in enumerate(snapshot.get("entry_exit_workflows") or (), start=1):
        checks = dict((item.get("evidence") or {}).get("checks") or {})
        failed_checks = [check_labels.get(code, code) for code, passed in checks.items() if not passed]
        evidence = item.get("evidence") or {}
        if item.get("workflow_stage") == "EXPENSIVE_GATES_FAILED":
            plateau = evidence.get("parameter_plateau") or {}
            control = evidence.get("negative_control") or {}
            if plateau and not plateau.get("passed"):
                failed_checks.append("нет устойчивого плато соседних параметров")
            if control and not control.get("passed"):
                failed_checks.append("не превосходит сопоставимый placebo-вход")
            if evidence.get("reason"):
                reason = str(evidence.get("reason"))
                failed_checks.append(reason_labels.get(reason, reason))
        failure_text = (" · Не пройдено: " + ", ".join(failed_checks)) if failed_checks else ""
        cards.append(RenderNodeV2(
            RenderNodeTypeV2.CARD, f"home.compact.optimizer.workflow.{index}",
            children=(
                _leaf(RenderNodeTypeV2.TITLE, f"home.compact.optimizer.workflow.{index}.title",
                      f"{item.get('symbol_group')} · {item.get('side_code')} · {item.get('candidate_code')}",
                      level="CARD"),
                _leaf(RenderNodeTypeV2.TEXT, f"home.compact.optimizer.workflow.{index}.stage",
                      workflow_labels.get(str(item.get("workflow_stage")),
                                          str(item.get("workflow_stage"))) + failure_text),
                _leaf(RenderNodeTypeV2.TEXT, f"home.compact.optimizer.workflow.{index}.gates",
                      f"Статистика: {item.get('statistical_verdict')} · "
                      f"дорогие проверки: {'PASS' if item.get('expensive_gates_pass') else ('FAIL' if item.get('workflow_stage') == 'EXPENSIVE_GATES_FAILED' else 'ожидание')} · "
                      f"V5 OOS: {'PASS' if item.get('v5_oos_pass') else 'ожидание'} · "
                      f"Paper-риск: {float(item.get('paper_risk_fraction') or 0)*100:.0f}%"),
            ),
        ))
    entry_labels = {"IMMEDIATE": "сразу после сигнала", "CONFIRM_1": "после подтверждения следующей свечой", "RETEST_3": "после ретеста в течение трёх свечей", "ADAPTIVE": "адаптивно: вход, подтверждение, ретест или пропуск по состоянию рынка"}
    instrument_labels = {"BR": "Нефть Brent", "NG": "Природный газ", "CNY": "Юань / рубль",
                         "GAZP": "Газпром", "LKOH": "Лукойл", "NVTK": "Новатэк",
                         "SBER": "Сбербанк", "SBERP": "Сбербанк-п", "VTBR": "ВТБ"}
    side_labels = {"LONG": "покупка", "SHORT": "продажа"}
    family_labels = {
        "ADAPTIVE_OR_SKIP": "адаптивный вход или пропуск",
        "CONFIRM_1": "подтверждение одной свечой",
        "RETEST_3": "ретест до трёх свечей",
    }
    status_labels = {
        "SHADOW_COLLECTING": "накапливает независимые Shadow-наблюдения",
        "PILOT_ACTIVE": "минимальный Paper-пилот активен",
        "PAPER_CONFIRMED": "Paper-профиль подтверждён",
        "ROLLED_BACK": "Paper-пилот автоматически откачен",
    }
    for index, item in enumerate(snapshot.get("adaptive_policy_families") or (), start=1):
        evidence = item.get("evidence") or {}
        quality = evidence.get("entry_quality") or {}
        exp = float(item.get("shadow_expectancy") or 0)
        pf = item.get("shadow_profit_factor")
        diagnostics = (
            f"задержка {quality.get('mean_delay_bars') or '—'} свеч.; "
            f"ухудшение входа {quality.get('mean_entry_slippage_r') or '—'}R; "
            f"MFE {quality.get('mean_mfe_r') or '—'}R; "
            f"MAE {quality.get('mean_mae_r') or '—'}R; "
            f"эффективность выхода {quality.get('mean_exit_efficiency') or '—'}"
        )
        cards.append(RenderNodeV2(
            RenderNodeTypeV2.CARD,
            f"home.compact.optimizer.family.{index}",
            children=(
                _leaf(
                    RenderNodeTypeV2.TITLE,
                    f"home.compact.optimizer.family.{index}.title",
                    f"{item.get('symbol')} · {side_labels.get(str(item.get('side_code')), item.get('side_code'))} · "
                    f"{family_labels.get(str(item.get('policy_family')), item.get('policy_family'))}",
                    level="CARD",
                ),
                _leaf(
                    RenderNodeTypeV2.TEXT,
                    f"home.compact.optimizer.family.{index}.evidence",
                    f"{int(item.get('shadow_observations') or 0)} независимых событий · "
                    f"Exp {exp:+.2f}R · PF {float(pf):.2f}" if pf is not None else
                    f"{int(item.get('shadow_observations') or 0)} независимых событий · Exp {exp:+.2f}R · PF —",
                ),
                _leaf(
                    RenderNodeTypeV2.TEXT,
                    f"home.compact.optimizer.family.{index}.diagnostics",
                    diagnostics,
                ),
                _leaf(
                    RenderNodeTypeV2.TEXT,
                    f"home.compact.optimizer.family.{index}.status",
                    status_labels.get(str(item.get("status_code")), str(item.get("status_code"))),
                ),
            ),
        ))
    legacy_recommendations = () if cards else (snapshot.get("entry_exit_recommendations") or ())
    for index, item in enumerate(legacy_recommendations, start=1):
        metrics = item.get("metrics") or {}
        paper_metrics = item.get("challenger_paper_metrics") or {}
        champion_metrics = item.get("champion_metrics") or {}
        challenger_status = str(item.get("challenger_status") or item.get("recommendation_status") or "")
        runtime_supported = (
            str(item.get("symbol_group")) in {"GAZP", "LKOH", "NVTK", "SBER", "SBERP", "VTBR"}
            and str(item.get("entry_mode")) in {"IMMEDIATE", "ADAPTIVE"}
        )
        ready = challenger_status == "READY_FOR_CHAMPION_CONFIRMATION" and runtime_supported
        active = bool(item.get("is_active_paper"))
        pairs, oos = int(item.get("pairs") or 0), int(item.get("oos_pairs") or 0)
        gate = metrics.get("adaptive_gate") or {}
        required_pairs = int(gate.get("min_pairs") or 80)
        required_oos = int(gate.get("min_oos") or 20)
        gate_name = ("расширенный период 40/10 → Challenger"
                     if gate.get("gate") == "DIVERSE_40_10_CHALLENGER" else "intraday 60/15")
        coverage = (f"{int(gate.get('active_days') or 0)} торговых дней, "
                    f"{int(gate.get('regimes') or 0)} режима(ов)")
        if active:
            champion_trades = int(champion_metrics.get("trades") or 0)
            exp = float(champion_metrics.get("expectancy_r") or 0)
            pf = float(champion_metrics.get("profit_factor") or 0)
            dd = float(champion_metrics.get("drawdown_r") or 0)
            dd_limit = float(champion_metrics.get("hard_drawdown_limit_r") or 3)
            cycles = int(item.get("consecutive_degraded_cycles") or 0)
            status_text = (f"Основной Paper-профиль · контроль {champion_trades} сделок: "
                           f"ожидание {exp:+.2f}R, PF {pf:.2f}, просадка {dd:.2f}R из {dd_limit:.2f}R. ")
            status_text += (f"Ухудшение подтверждено {cycles} из 2 циклов. " if cycles else
                            "Критерии отката не сработали. ")
            status_text += "Назначение и обновление автоматические; REAL выключен."
        elif challenger_status == "ROLLED_BACK":
            reason_labels = {"HARD_DRAWDOWN_BREACH": "превышен аварийный лимит просадки",
                             "NEGATIVE_EXPECTANCY_OR_LOW_PF": "два цикла отрицательного ожидания или низкого PF"}
            reason = reason_labels.get(str(item.get("rollback_reason") or ""),
                                       str(item.get("rollback_reason") or "защитный критерий"))
            status_text = f"Автоматический откат Paper: {reason}. Предыдущий профиль восстановлен; REAL не затронут."
        elif ready:
            status_text = "Challenger прошёл forward-проверку и будет автоматически назначен основным Paper."
        elif challenger_status in {"PAPER_CHALLENGER", "KEEP_PAPER_CHALLENGER"}:
            forward_pairs = int(paper_metrics.get("pairs") or 0)
            forward_oos = int(paper_metrics.get("oos_pairs") or 0)
            status_text = f"Paper Challenger: forward-сравнение {forward_pairs} из 30 пар; OOS {forward_oos} из 10."
            if challenger_status == "KEEP_PAPER_CHALLENGER":
                status_text += " Преимущество пока не подтверждено — продолжаем наблюдение."
        elif item.get("recommendation_status") == "READY_FOR_PAPER_CONFIRMATION" and not runtime_supported:
            status_text = "Shadow-проверки пройдены, но отложенный вход пока не поддерживается Paper runtime."
        else:
            status_text = (f"Shadow · {gate_name}: {pairs} из {required_pairs} независимых пар; "
                           f"OOS {oos} из {required_oos}; покрытие: {coverage}.")
            if metrics.get("oos_provisional"):
                status_text += " OOS пока предварительный и не разрешает продвижение."
            if challenger_status == "SHADOW_EARLY_EVIDENCE" or pairs >= 40:
                status_text += " Предварительные данные есть, но продвижение ещё запрещено."
        stop_text = f"{float(item.get('stop_atr') or 0):.1f}".replace(".", ",")
        take_text = f"{float(item.get('take_atr') or 0):.1f}".replace(".", ",")
        trail_after = item.get("trail_after_r")
        trail_atr = item.get("trail_atr")
        trail_text = ""
        if trail_after is not None and trail_atr is not None:
            trail_after_text = f"{float(trail_after):.1f}".replace(".", ",")
            trail_atr_text = f"{float(trail_atr):.1f}".replace(".", ",")
            trail_text = f" Трейлинг после {trail_after_text}R, дистанция {trail_atr_text} ATR."
        parameters = (
            f"Кандидат Shadow: вход {entry_labels.get(str(item.get('entry_mode')), item.get('entry_mode'))}; "
            f"стоп {stop_text} ATR; цель {take_text} ATR.{trail_text}"
        )
        negative = metrics.get("negative_control") or {}
        plateau = metrics.get("parameter_plateau") or {}
        if negative:
            control_text = ("пройден" if negative.get("passed") else "не пройден")
            parameters += (
                f" Контроль случайного преимущества: {control_text}, "
                f"пар {int(negative.get('pairs') or 0)}."
            )
        if plateau:
            plateau_text = ("устойчивый диапазон" if plateau.get("passed")
                            else "устойчивый диапазон ещё не подтверждён")
            parameters += f" Параметры: {plateau_text}."
        if item.get("family_code"):
            family_names = {"EQUITIES": "акции", "OIL": "нефть", "GAS": "газ",
                            "FX": "валюты", "METALS": "металлы", "OTHER": "прочие"}
            parameters += (
                f" Семейство «{family_names.get(str(item['family_code']), item['family_code'])}»: "
                f"{int(item.get('family_pairs') or 0)} пар, "
                f"OOS {int(item.get('family_oos_pairs') or 0)}; только диагностический ориентир."
            )
        if item.get("adaptive_candidate_code"):
            adaptive_metrics = item.get("adaptive_metrics") or {}
            adaptive_gate = adaptive_metrics.get("adaptive_gate") or {}
            adaptive_required = int(adaptive_gate.get("min_pairs") or 60)
            decisions = adaptive_metrics.get("entry_decisions") or {}
            decision_labels = {"IMMEDIATE": "сразу", "CONFIRM_1": "подтверждение",
                               "RETEST_3": "ретест", "SKIP": "пропуск"}
            decision_text = ", ".join(
                f"{decision_labels.get(code, code)} {int(count)}"
                for code, count in decisions.items()
            ) or "решений пока нет"
            parameters += (
                f" Адаптивный вход: Shadow, "
                f"{int(item.get('adaptive_pairs') or 0)} из {adaptive_required} пар; "
                f"сам выбирает вход сразу, подтверждение, ретест или пропуск; {decision_text}."
            )
        if metrics.get("shadow_only"):
            parameters += (
                f" Экспертная политика: "
                f"{metrics.get('expert_policy_label') or 'специализированный фильтр'}. "
                "Только Shadow; автоматическое назначение в Paper запрещено."
            )
        champion_code = str(item.get("champion_candidate_code") or "CURRENT_PAPER")
        challenger_code = str(item.get("challenger_candidate_code") or item.get("candidate_code") or "—")
        paper_stop = item.get("paper_stop_atr")
        paper_take = item.get("paper_take_atr")
        if paper_stop is None or paper_take is None:
            paper_description = (
                "Действующий Paper: встроенный профиль стратегии; оптимизированный профиль "
                "в БД ещё не назначен"
            )
        else:
            paper_entry = entry_labels.get(str(item.get("paper_entry_mode")), item.get("paper_entry_mode"))
            paper_description = (
                f"Действующий Paper: {champion_code}; вход {paper_entry}; "
                f"стоп {float(paper_stop):.1f} ATR; цель {float(paper_take):.1f} ATR"
            ).replace(".", ",")
            if item.get("paper_trail_after_r") is not None and item.get("paper_trail_atr") is not None:
                paper_description += (
                    f"; трейлинг после {float(item['paper_trail_after_r']):.1f}R, "
                    f"дистанция {float(item['paper_trail_atr']):.1f} ATR"
                ).replace(".", ",")
        hard_limits = {
            "BR": "аварийный предел 12 ч, в подтверждённом тренде до 24 ч",
            "NG": "аварийный предел 6 ч, в подтверждённом тренде до 12 ч",
            "CNY": "аварийный предел 8 ч, в подтверждённом тренде до 16 ч",
            "USD": "аварийный предел 8 ч, в подтверждённом тренде до 16 ч",
            "GOLD": "аварийный предел 10 ч, в подтверждённом тренде до 20 ч",
        }
        hard_limit_text = hard_limits.get(str(item.get("symbol_group") or "").upper(),
                                          "аварийный предел 8 ч, в подтверждённом тренде до 16 ч")
        comparison = f"{paper_description}. {hard_limit_text}. Challenger: {challenger_code}."
        actual_exp = paper_metrics.get("actual_expectancy_r", metrics.get("actual_expectancy_r"))
        challenger_exp = paper_metrics.get("challenger_expectancy_r", metrics.get("shadow_expectancy_r"))
        delta = paper_metrics.get("expectancy_delta_r")
        if actual_exp is not None and challenger_exp is not None:
            comparison += f" Expectancy: {float(actual_exp):+.2f}R → {float(challenger_exp):+.2f}R"
            comparison += f"; разница {float(delta):+.2f}R." if delta is not None else "."
        group = str(item.get("symbol_group") or "")
        cards.append(RenderNodeV2(
            RenderNodeTypeV2.CARD, f"home.compact.optimizer.card.{index}",
            state=RenderNodeStateV2(status_code="ACTIVE" if active else ("OK" if ready else "WARNING")),
            children=(
                _leaf(RenderNodeTypeV2.TITLE, f"home.compact.optimizer.card.{index}.title",
                      f"{instrument_labels.get(group, group)} · {side_labels.get(str(item.get('side_code')), item.get('side_code'))}", level="CARD"),
                _leaf(RenderNodeTypeV2.TEXT, f"home.compact.optimizer.card.{index}.parameters", parameters),
                _leaf(RenderNodeTypeV2.TEXT, f"home.compact.optimizer.card.{index}.comparison", comparison),
                _leaf(RenderNodeTypeV2.TEXT, f"home.compact.optimizer.card.{index}.status", status_text),
            ),
        ))
    if not cards:
        cards.append(RenderNodeV2(RenderNodeTypeV2.CARD, "home.compact.optimizer.empty", children=(
            _leaf(RenderNodeTypeV2.TEXT, "home.compact.optimizer.empty.text", "Первый расчёт ещё не завершён."),
        )))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "home.compact.optimizer", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.optimizer.title", "Текущий Paper и кандидаты", level="SECTION"),
        _leaf(RenderNodeTypeV2.TEXT, "home.compact.optimizer.help", "Система сравнивает кандидатов на одинаковых сигналах, проверяет их против безусловного входа, соседних ATR-параметров и диагностической статистики семейства, затем назначает победителя и при ухудшении откатывает Paper. Семейные данные ускоряют отбор, но не разрешают Paper. Реальная торговля не включается."),
        RenderNodeV2(RenderNodeTypeV2.GRID, "home.compact.optimizer.cards", children=tuple(cards)),
    ))


def _oos_evidence_section(snapshot):
    evidence = snapshot.get("v5_oos_evidence") or {}
    runs = list(snapshot.get("v5_oos_runs") or ())

    def fmt(value, digits=2):
        return "нет данных" if value is None else f"{float(value):.{digits}f}".replace(".", ",")

    top_trade = float(evidence.get("top_trade_profit_share") or 0)
    top_symbol = float(evidence.get("top_symbol_profit_share") or 0)
    rows = [
        _row("oos.paper", "Текущий Paper",
             f"{int(evidence.get('paper_trades') or 0)} закрытых сделок · "
             f"PF {fmt(evidence.get('paper_profit_factor'))} · "
             f"медиана {fmt(evidence.get('paper_median_pnl'))} ₽"),
        _row("oos.freeze", "Фиксация гипотезы",
             f"лучшая однородная группа: "
             f"{int(evidence.get('best_training_trades') or 0)} из 15 сделок · "
             f"ожидают накопления {int(evidence.get('waiting_admissions') or 0)}",
             status="OK" if int(evidence.get("frozen_admissions") or 0) else "WARNING"),
        _row("oos.isolation", "Проверка на новых сделках",
             f"собирается {int(evidence.get('collecting_runs') or 0)} · "
             f"PASS {int(evidence.get('passed_runs') or 0)} · "
             f"FAIL {int(evidence.get('failed_runs') or 0)} · "
             f"включено {int(evidence.get('oos_included') or 0)} · "
             f"исключено аудитом {int(evidence.get('oos_excluded') or 0)}",
             status="OK" if int(evidence.get("passed_runs") or 0) else "WARNING"),
        _row("oos.controls", "Shadow против placebo",
             f"Shadow {fmt(evidence.get('shadow_expectancy_r'))}R · "
             f"placebo {fmt(evidence.get('placebo_expectancy_r'))}R",
             status="OK" if evidence.get("shadow_expectancy_r") is not None
             and evidence.get("placebo_expectancy_r") is not None
             and float(evidence["shadow_expectancy_r"]) > float(evidence["placebo_expectancy_r"])
             else "WARNING"),
        _row("oos.concentration", "Концентрация прибыли",
             f"лучшая сделка {top_trade:.0%} · лучший инструмент {top_symbol:.0%}",
             status="WARNING" if top_trade > 0.35 or top_symbol > 0.60 else "OK"),
    ]
    status_labels = {
        "COLLECTING": "Идёт независимая проверка",
        "OOS_PASS": "Edge подтверждён",
        "OOS_FAIL": "Edge не подтверждён",
        "ERROR": "Ошибка проверки",
    }
    for index, run in enumerate(runs[:5], start=1):
        status = str(run.get("status_code") or "COLLECTING")
        rows.append(_row(
            f"oos.run.{index}",
            f"{run.get('symbol') or '—'} · {run.get('side_code') or '—'}",
            f"{status_labels.get(status, 'Ожидает данных')}: "
            f"{int(run.get('observations_included') or 0)} из "
            f"{int(run.get('minimum_observations') or 20)} будущих наблюдений · "
            f"PF {fmt(run.get('profit_factor'))} · Exp {fmt(run.get('expectancy'))}",
            status="OK" if status == "OOS_PASS" else
                   "BLOCKED" if status == "OOS_FAIL" else "WARNING",
            source="analytics.v5_oos_run_v1", source_as_of=run.get("updated_at"),
        ))
    rows.append(_leaf(
        RenderNodeTypeV2.TEXT, "home.compact.oos.help",
        "Paper-история только замораживает гипотезу. PASS считается на сделках "
        "после момента её фиксации; повторное использование запрещено. REAL выключен.",
    ))
    return RenderNodeV2(RenderNodeTypeV2.SECTION, "home.compact.oos", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.oos.title",
              "Доказательность V5 OOS", level="SECTION"),
        RenderNodeV2(RenderNodeTypeV2.METRIC_LIST,
                     "home.compact.oos.metrics", children=tuple(rows)),
    ))


def render_home_compact_v1(snapshot, *, timezone_code="Europe/Moscow"):
    page = RenderNodeV2(RenderNodeTypeV2.PAGE, "home.compact.page", children=(
        _leaf(RenderNodeTypeV2.TITLE, "home.compact.title", "MarketCore", level="PAGE"),
        _leaf(RenderNodeTypeV2.SUBTITLE, "home.compact.subtitle",
              "Поиск преимущества · без реальных сделок"),
        _now_section(snapshot),
        _workflow_section(snapshot),
        _lightweight_statistics_section(snapshot),
        _progress_section(snapshot),
        _recent_trades_section(snapshot, timezone_code, futures=False),
        _recent_trades_section(snapshot, timezone_code, futures=True),
        _shadow_dynamics_section(snapshot),
        _oos_evidence_section(snapshot),
        _optimizer_section(snapshot),
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
