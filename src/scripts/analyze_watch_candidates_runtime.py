from __future__ import annotations

import hashlib
import json
import os
import psycopg2
import requests
from datetime import datetime, timezone

from finam_core.notifications.telegram_notifier import TelegramNotifier
from finam_core.runtime.runtime_decision_digest import build_runtime_digest
from finam_core.runtime.runtime_capital_allocator import RuntimeCapitalAllocator
from finam_core.runtime.signal_probability_estimator import SignalProbabilityEstimator
from finam_core.runtime.net_trade_evaluator import NetTradeEvaluator
from finam_core.runtime.institutional_trade_quality_score import InstitutionalTradeQualityScorer
from finam_core.runtime.capital_growth_mode import CapitalGrowthMode
from finam_core.runtime.risk_per_trade_sizing import RiskPerTradeSizer
from finam_core.runtime.capital_growth_profile import CapitalGrowthProfile
from finam_core.runtime.capital_growth_daily_loss_guard import CapitalGrowthDailyLossGuard
from finam_core.runtime.capital_growth_portfolio_governor import CapitalGrowthPortfolioGovernor
from finam_core.runtime.portfolio_aware_signal_filter import PortfolioAwareSignalFilter


def load_watch_candidates(cur, limit: int = 10) -> list[dict]:
    cur.execute(
        """
        select
            id,
            symbol,
            strategy,
            regime,
            score,
            reason,
            raw_json
        from radar_candidate_analysis
        where decision = 'WATCH'
          and source = 'market_radar_top10'
        order by created_at desc, id desc
        limit %s
        """,
        (limit,),
    )

    rows = []
    for r in cur.fetchall():
        rows.append(
            {
                "analysis_id": int(r[0]),
                "symbol": str(r[1]),
                "strategy": str(r[2] or "UNKNOWN"),
                "regime": str(r[3] or "UNKNOWN"),
                "score": float(r[4] or 0.0),
                "reason": str(r[5] or ""),
                "raw_json": r[6] or {},
            }
        )
    return rows



def normalize_moex_secid(symbol: str) -> str:
    """Русский комментарий: LKOH@MISX -> LKOH."""
    return str(symbol or "").split("@", 1)[0]


def load_moex_last_price(symbol: str) -> float | None:
    """Русский комментарий: получает последнюю цену акции с MOEX ISS."""
    secid = normalize_moex_secid(symbol)
    if not secid:
        return None

    url = (
        "https://iss.moex.com/iss/engines/stock/markets/shares/"
        f"securities/{secid}.json"
    )

    try:
        r = requests.get(url, timeout=10)
        if r.status_code != 200:
            return None

        data = r.json()
        marketdata = data.get("marketdata", {})
        columns = marketdata.get("columns", [])
        rows = marketdata.get("data", [])

        if not columns or not rows:
            return None

        idx = {name: i for i, name in enumerate(columns)}

        for row in rows:
            # Русский комментарий: предпочитаем LAST, fallback на MARKETPRICE / LCURRENTPRICE.
            for key in ("LAST", "MARKETPRICE", "LCURRENTPRICE"):
                if key in idx:
                    value = row[idx[key]]
                    if value is not None:
                        price = float(value)
                        if price > 0:
                            return price

    except Exception:
        return None

    return None


def build_trade_setup(candidate: dict, price: float) -> dict:
    """Русский комментарий: строит entry/stop/take по типу стратегии."""
    strategy = str(candidate.get("strategy") or "").upper()
    regime = str(candidate.get("regime") or "")

    if price <= 0:
        return {
            "decision": "WATCH",
            "reason": "цена недоступна",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    if "MEAN_REVERSION" in strategy or "OVERSOLD" in regime.upper():
        # Русский комментарий: MeanReversionSetup v2 — более сбалансированный RR.
        # Вход по текущей цене, короткий защитный стоп, цель на технический отскок.
        entry = price
        stop = price * 0.985
        take = price * 1.030
        setup_name = "отскок после снижения"
    elif "BREAKOUT" in strategy or "TREND" in regime.upper():
        entry = price * 1.002
        stop = price * 0.985
        take = price * 1.035
        setup_name = "пробой / продолжение импульса"
    else:
        entry = price
        stop = price * 0.980
        take = price * 1.030
        setup_name = "универсальный сетап наблюдения"

    risk = abs(entry - stop)
    reward = abs(take - entry)
    rr = reward / risk if risk > 0 else 0.0

    if rr >= 1.5:
        decision = "ALERT"
    else:
        decision = "WATCH"

    return {
        "decision": decision,
        "reason": f"{setup_name}; price={price:.4f}; rr={rr:.2f}",
        "entry_price": round(entry, 4),
        "stop_loss": round(stop, 4),
        "take_profit": round(take, 4),
        "risk_reward": round(rr, 4),
    }

def make_runtime_decision(candidate: dict) -> dict:
    """Русский комментарий: получает реальную цену MOEX и строит strategy-specific setup."""
    score = float(candidate.get("score") or 0.0)
    strategy = str(candidate.get("strategy") or "UNKNOWN")

    if score <= 0:
        return {
            "decision": "IGNORE",
            "reason": "нулевой score после runtime-проверки",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    if strategy == "UNKNOWN":
        return {
            "decision": "WATCH",
            "reason": "нет стратегии; оставлен в наблюдении",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    price = load_moex_last_price(candidate["symbol"])

    if price is None:
        return {
            "decision": "WATCH",
            "reason": "MOEX цена недоступна; оставлен в наблюдении",
            "entry_price": None,
            "stop_loss": None,
            "take_profit": None,
            "risk_reward": None,
        }

    return build_trade_setup(candidate, price)



def get_correlation_group(cur, symbol: str) -> str:
    cur.execute(
        """
        select correlation_group
        from signal_correlation_groups
        where symbol = %s
        """,
        (symbol,),
    )
    row = cur.fetchone()
    return str(row[0]) if row else "OTHER"


def active_group_alert_count(cur, group_name: str, ttl_minutes: int) -> int:
    cur.execute(
        """
        select count(*)
        from signal_alert_dedup d
        join signal_correlation_groups g on g.symbol = d.symbol
        where g.correlation_group = %s
          and d.last_sent_at > now() - (%s || ' minutes')::interval
        """,
        (group_name, str(ttl_minutes)),
    )
    return int(cur.fetchone()[0] or 0)


def apply_correlation_filter(cur, candidate: dict, decision: dict, max_per_group: int, ttl_minutes: int) -> dict:
    """Русский комментарий: ограничивает число активных ALERT в одной факторной группе."""
    if decision.get("decision") != "ALERT":
        return decision

    group_name = get_correlation_group(cur, candidate["symbol"])
    active_count = active_group_alert_count(cur, group_name, ttl_minutes)

    decision["correlation_group"] = group_name
    decision["active_group_alerts"] = active_count

    if active_count >= max_per_group:
        decision = dict(decision)
        decision["decision"] = "WATCH"
        decision["reason"] = (
            f"корреляционный лимит: группа={group_name}; "
            f"активных_сигналов={active_count}; лимит={max_per_group}"
        )

    return decision



def strategy_display_name(strategy: str) -> str:
    """Русский комментарий: человекочитаемые названия стратегий."""
    mapping = {
        "MEAN_REVERSION_EQUITY": "Отскок после снижения",
        "VOLATILITY_BREAKOUT_EQUITY": "Пробой волатильности",
        "TREND_FOLLOWING": "Следование за трендом",
        "MOMENTUM_BREAKOUT": "Импульсный пробой",
        "RANGE_REVERSION": "Возврат к диапазону",
    }

    return mapping.get(strategy, strategy)

def load_latest_portfolio_context(cur) -> dict:
    """Русский комментарий: читает последний снимок портфеля для расчёта допустимого капитала."""
    cur.execute(
        """
        select
            coalesce(equity, 0),
            coalesce(cash, 0),
            coalesce(margin_utilization_pct, 0),
            coalesce(drawdown, 0),
            coalesce(free_margin, 0)
        from portfolio_snapshots
        order by ts desc
        limit 1
        """
    )
    row = cur.fetchone()

    if row is None:
        return {
            "equity": 0.0,
            "cash": 0.0,
            "margin_utilization_pct": 0.0,
            "drawdown": 0.0,
            "free_margin": 0.0,
        }

    return {
        "equity": float(row[0] or 0),
        "cash": float(row[1] or 0),
        "margin_utilization_pct": float(row[2] or 0),
        "drawdown": float(row[3] or 0),
        "free_margin": float(row[4] or 0),
    }


def apply_capital_allocator(cur, candidate: dict, decision: dict) -> dict:
    """Русский комментарий: добавляет к ALERT допустимый размер позиции и risk multiplier."""
    if decision.get("decision") != "ALERT":
        return decision

    portfolio = load_latest_portfolio_context(cur)

    correlation_pressure = int(decision.get("active_group_alerts") or 0)
    signal_score = float(candidate.get("score") or 0.0)
    risk_reward = float(decision.get("risk_reward") or 0.0)

    allocation = RuntimeCapitalAllocator().allocate(
        equity=portfolio["equity"],
        cash=portfolio["cash"],
        margin_utilization_pct=portfolio["margin_utilization_pct"],
        drawdown=portfolio["drawdown"],
        free_margin=portfolio["free_margin"],
        signal_score=signal_score,
        risk_reward=risk_reward,
        correlation_pressure=correlation_pressure,
        runtime_severity="INFO",
    )

    decision = dict(decision)
    decision["capital_allowed"] = allocation.allowed
    decision["risk_multiplier"] = allocation.risk_multiplier
    decision["max_position_value"] = allocation.max_position_value
    decision["capital_reason"] = allocation.reason

    if not allocation.allowed:
        decision["decision"] = "WATCH"
        decision["reason"] = f"capital_allocator: {allocation.reason}"

    return decision


def estimate_signal_probability(cur, candidate: dict) -> dict:
    """Русский комментарий: оценивает вероятность TP/SL по истории signal_lifecycle."""
    strategy = str(candidate.get("strategy") or "")
    regime = str(candidate.get("regime") or "")

    cur.execute(
        """
        select
            count(*) filter (where close_reason = 'TAKE_PROFIT') as tp_hits,
            count(*) filter (where close_reason = 'STOP_LOSS') as sl_hits,
            count(*) filter (where state = 'EXPIRED' or close_reason = 'TIME_EXPIRED') as expired
        from signal_lifecycle
        where strategy = %s
          and regime = %s
          and state in ('CLOSED','EXPIRED')
        """,
        (strategy, regime),
    )

    row = cur.fetchone()
    tp_hits = int(row[0] or 0)
    sl_hits = int(row[1] or 0)
    expired = int(row[2] or 0)

    probability = SignalProbabilityEstimator().estimate(
        tp_hits=tp_hits,
        sl_hits=sl_hits,
        expired=expired,
    )

    # Русский комментарий: если истории мало, используем консервативный baseline.
    if probability.sample_size < 10:
        return {
            "probability_tp": 0.50,
            "probability_sl": 0.45,
            "probability_expire": 0.05,
            "probability_sample_size": probability.sample_size,
            "probability_source": "baseline_low_sample",
        }

    return {
        "probability_tp": probability.probability_tp,
        "probability_sl": probability.probability_sl,
        "probability_expire": probability.probability_expire,
        "probability_sample_size": probability.sample_size,
        "probability_source": "signal_lifecycle_history",
    }


def apply_net_trade_evaluation(cur, candidate: dict, decision: dict) -> dict:
    """Русский комментарий: добавляет вероятность, комиссии, налог и чистое матожидание."""
    if decision.get("decision") != "ALERT":
        return decision

    entry = float(decision.get("entry_price") or 0.0)
    stop = float(decision.get("stop_loss") or 0.0)
    take = float(decision.get("take_profit") or 0.0)
    max_position_value = float(decision.get("max_position_value") or 0.0)

    if entry <= 0 or stop <= 0 or take <= 0 or max_position_value <= 0:
        return decision

    qty = int(max_position_value / entry)
    if qty <= 0:
        decision = dict(decision)
        decision["decision"] = "WATCH"
        decision["reason"] = "net_trade_evaluator: qty<=0"
        return decision

    prob = estimate_signal_probability(cur, candidate)

    evaluation = NetTradeEvaluator().evaluate(
        entry_price=entry,
        stop_loss=stop,
        take_profit=take,
        qty=qty,
        probability_tp=float(prob["probability_tp"]),
        probability_sl=float(prob["probability_sl"]),
    )

    decision = dict(decision)
    decision["recommended_qty"] = qty
    decision.update(prob)
    decision["gross_profit"] = evaluation.gross_profit
    decision["gross_loss"] = evaluation.gross_loss
    decision["commissions"] = evaluation.commissions
    decision["estimated_tax"] = evaluation.estimated_tax
    decision["slippage_cost"] = evaluation.slippage_cost
    decision["net_take_profit"] = evaluation.net_take_profit
    decision["net_stop_loss"] = evaluation.net_stop_loss
    decision["expected_value"] = evaluation.expected_value
    decision["expected_value_pct"] = evaluation.expected_value_pct

    if evaluation.expected_value <= 0:
        decision["decision"] = "WATCH"
        decision["reason"] = f"net_trade_evaluator: expected_value<=0; ev={evaluation.expected_value}"

    return decision


def apply_trade_quality_score(candidate: dict, decision: dict) -> dict:
    """Русский комментарий: добавляет итоговый institutional score к ALERT."""
    if decision.get("decision") != "ALERT":
        return decision

    score = InstitutionalTradeQualityScorer().score(
        probability_tp=float(decision.get("probability_tp") or 0.0),
        probability_sl=float(decision.get("probability_sl") or 0.0),
        expected_value_pct=float(decision.get("expected_value_pct") or 0.0),
        risk_reward=float(decision.get("risk_reward") or 0.0),
        signal_score=float(candidate.get("score") or 0.0),
        correlation_pressure=int(decision.get("active_group_alerts") or 0),
        risk_multiplier=float(decision.get("risk_multiplier") or 0.0),
    )

    decision = dict(decision)
    decision["trade_quality_score"] = score.score
    decision["trade_quality_grade"] = score.grade
    decision["trade_quality_reason"] = score.reason

    return decision



def load_daily_loss_guard_context(cur) -> dict:
    """Русский комментарий: проверяет дневную просадку по текущему профилю разгона."""
    import os

    profile = CapitalGrowthProfile().load(
        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
    )

    cur.execute(
        """
        select
            coalesce(equity, 0),
            coalesce(realized_pnl, 0) + coalesce(unrealized_pnl, 0) as daily_pnl
        from portfolio_snapshots
        order by ts desc
        limit 1
        """
    )

    row = cur.fetchone()

    if row is None:
        return {
            "daily_loss_allowed": False,
            "daily_loss_reason": "no_portfolio_snapshot",
        }

    decision = CapitalGrowthDailyLossGuard().check(
        equity=float(row[0] or 0.0),
        daily_pnl=float(row[1] or 0.0),
        max_daily_loss_pct=profile.max_daily_loss_pct,
    )

    return {
        "daily_loss_allowed": decision.allowed,
        "daily_loss_reason": decision.reason,
        "daily_pnl": decision.daily_pnl,
        "daily_loss_pct": decision.daily_loss_pct,
        "daily_loss_limit_pct": decision.limit_pct,
    }


def load_capital_growth_governor_context(cur) -> dict:
    """Русский комментарий: проверяет лимит активных growth-сделок по профилю."""
    import os

    profile = CapitalGrowthProfile().load(
        os.getenv("CAPITAL_GROWTH_PROFILE", "growth")
    )

    cur.execute(
        """
        select count(*)
        from execution_intents
        where intent_state in ('SENT','ACK','PARTIAL_FILL','FILLED')
          and coalesce(raw_json->>'capital_growth_mode','') <> ''
        """
    )

    active_growth_trades = int(cur.fetchone()[0] or 0)

    decision = CapitalGrowthPortfolioGovernor().check(
        active_growth_trades=active_growth_trades,
        max_active_growth_trades=profile.max_active_growth_trades,
    )

    return {
        "growth_governor_allowed": decision.allowed,
        "active_growth_trades": decision.active_growth_trades,
        "max_active_growth_trades": decision.max_active_growth_trades,
        "growth_governor_reason": decision.reason,
    }

def apply_risk_per_trade_sizing(cur, candidate: dict, decision: dict) -> dict:
    """Русский комментарий: пересчитывает qty через риск до стопа, а не только через капитал."""
    if decision.get("decision") != "ALERT":
        return decision

    portfolio = load_latest_portfolio_context(cur)

    equity = float(portfolio.get("equity") or 0.0)
    margin_utilization_pct = float(portfolio.get("margin_utilization_pct") or 0.0)
    portfolio_heat = margin_utilization_pct / 100.0

    daily_loss = load_daily_loss_guard_context(cur)
    governor = load_capital_growth_governor_context(cur)

    if not bool(governor.get("growth_governor_allowed")):
        decision = dict(decision)
        decision["decision"] = "WATCH"
        decision["growth_governor_allowed"] = governor.get("growth_governor_allowed")
        decision["active_growth_trades"] = governor.get("active_growth_trades")
        decision["max_active_growth_trades"] = governor.get("max_active_growth_trades")
        decision["growth_governor_reason"] = governor.get("growth_governor_reason")
        decision["reason"] = f"capital_growth_governor: {governor.get('growth_governor_reason')}"
        return decision

    growth = CapitalGrowthMode().decide(
        trade_quality_grade=str(decision.get("trade_quality_grade") or "D"),
        trade_quality_score=float(decision.get("trade_quality_score") or 0.0),
        expected_value=float(decision.get("expected_value") or 0.0),
        probability_tp=float(decision.get("probability_tp") or 0.0),
        probability_sl=float(decision.get("probability_sl") or 0.0),
        risk_reward=float(decision.get("risk_reward") or 0.0),
        portfolio_heat=portfolio_heat,
        runtime_severity="INFO",
        daily_loss_allowed=bool(daily_loss.get("daily_loss_allowed")),
        daily_loss_reason=str(daily_loss.get("daily_loss_reason") or ""),
    )

    decision = dict(decision)
    decision["capital_growth_allowed"] = growth.allowed
    decision["capital_growth_mode"] = growth.mode
    decision["capital_growth_risk_pct"] = growth.risk_pct
    decision["capital_growth_reason"] = growth.reason
    decision["daily_loss_allowed"] = daily_loss.get("daily_loss_allowed")
    decision["daily_pnl"] = daily_loss.get("daily_pnl")
    decision["daily_loss_pct"] = daily_loss.get("daily_loss_pct")
    decision["daily_loss_limit_pct"] = daily_loss.get("daily_loss_limit_pct")
    decision["daily_loss_reason"] = daily_loss.get("daily_loss_reason")
    decision["growth_governor_allowed"] = governor.get("growth_governor_allowed")
    decision["active_growth_trades"] = governor.get("active_growth_trades")
    decision["max_active_growth_trades"] = governor.get("max_active_growth_trades")
    decision["growth_governor_reason"] = governor.get("growth_governor_reason")
    decision["growth_governor_allowed"] = governor.get("growth_governor_allowed")
    decision["active_growth_trades"] = governor.get("active_growth_trades")
    decision["max_active_growth_trades"] = governor.get("max_active_growth_trades")
    decision["growth_governor_reason"] = governor.get("growth_governor_reason")

    size = RiskPerTradeSizer().size(
        equity=equity,
        risk_pct=float(growth.risk_pct or 0.0),
        entry_price=float(decision.get("entry_price") or 0.0),
        stop_loss=float(decision.get("stop_loss") or 0.0),
        max_position_value=float(decision.get("max_position_value") or 0.0),
    )

    decision["risk_sizing_allowed"] = size.allowed
    decision["recommended_qty"] = size.qty
    decision["risk_rub"] = size.risk_rub
    decision["risk_per_unit"] = size.risk_per_unit
    decision["capital_used"] = size.capital_used
    decision["risk_sizing_reason"] = size.reason

    if not growth.allowed:
        decision["decision"] = "WATCH"
        decision["reason"] = f"capital_growth_mode: {growth.reason}"

    elif not size.allowed:
        decision["decision"] = "WATCH"
        decision["reason"] = f"risk_per_trade_sizing: {size.reason}"

    return decision

def save_runtime_analysis(cur, candidate: dict, decision: dict) -> None:
    payload = {
        "source_analysis_id": candidate["analysis_id"],
        "candidate": candidate,
        "runtime_decision": decision,
        "calculated_at": datetime.now(timezone.utc).isoformat(),
    }

    cur.execute(
        """
        insert into radar_candidate_analysis (
            symbol,
            source,
            decision,
            reason,
            strategy,
            regime,
            entry_price,
            stop_loss,
            take_profit,
            risk_reward,
            score,
            raw_json
        )
        values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb)
        """,
        (
            candidate["symbol"],
            "watch_candidate_runtime_analyzer",
            decision["decision"],
            decision["reason"],
            candidate["strategy"],
            candidate["regime"],
            decision["entry_price"],
            decision["stop_loss"],
            decision["take_profit"],
            decision["risk_reward"],
            candidate["score"],
            json.dumps(payload, ensure_ascii=False, default=str),
        ),
    )



def build_alert_key(candidate: dict, decision: dict) -> str:
    raw = "|".join([
        str(candidate.get("symbol") or ""),
        str(candidate.get("strategy") or ""),
        str(candidate.get("regime") or ""),
        str(decision.get("decision") or ""),
    ])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def should_send_alert(cur, candidate: dict, decision: dict, ttl_minutes: int) -> bool:
    """Русский комментарий: антидубль ALERT по ключу symbol+strategy+regime+decision."""
    alert_key = build_alert_key(candidate, decision)

    cur.execute(
        """
        select 1
        from signal_alert_dedup
        where alert_key = %s
          and last_sent_at > now() - (%s || ' minutes')::interval
        limit 1
        """,
        (alert_key, str(ttl_minutes)),
    )

    return cur.fetchone() is None


def mark_alert_sent(cur, candidate: dict, decision: dict) -> None:
    alert_key = build_alert_key(candidate, decision)

    payload = {
        "candidate": candidate,
        "decision": decision,
    }

    cur.execute(
        """
        insert into signal_alert_dedup (
            alert_key,
            symbol,
            strategy,
            regime,
            decision,
            last_sent_at,
            payload
        )
        values (%s,%s,%s,%s,%s,now(),%s::jsonb)
        on conflict (alert_key) do update set
            last_sent_at = excluded.last_sent_at,
            payload = excluded.payload
        """,
        (
            alert_key,
            candidate.get("symbol"),
            candidate.get("strategy"),
            candidate.get("regime"),
            decision.get("decision"),
            json.dumps(payload, ensure_ascii=False, default=str),
        ),
    )


def save_signal_lifecycle(cur, candidate: dict, decision: dict) -> None:
    """Русский комментарий: регистрирует новый ALERT в жизненном цикле сигналов."""
    if decision.get("decision") != "ALERT":
        return

    signal_id = build_alert_key(candidate, decision)

    cur.execute(
        """
        insert into signal_lifecycle (
            signal_id,
            symbol,
            strategy,
            regime,
            state,
            entry_price,
            stop_loss,
            take_profit,
            risk_reward,
            expire_at,
            raw_json
        )
        values (
            %s,%s,%s,%s,'NEW',%s,%s,%s,%s,
            now() + interval '120 minutes',
            %s::jsonb
        )
        on conflict(signal_id) do nothing
        """,
        (
            signal_id,
            candidate.get("symbol"),
            candidate.get("strategy"),
            candidate.get("regime"),
            decision.get("entry_price"),
            decision.get("stop_loss"),
            decision.get("take_profit"),
            decision.get("risk_reward"),
            json.dumps(
                {"candidate": candidate, "decision": decision},
                ensure_ascii=False,
                default=str,
            ),
        ),
    )

def send_alert_if_any(cur, notifier: TelegramNotifier, candidate: dict, decision: dict, ttl_minutes: int) -> int:
    if decision["decision"] != "ALERT":
        return 0

    # Русский комментарий: lifecycle должен сохраняться даже если Telegram ALERT подавлен TTL/dedup.
    save_signal_lifecycle(cur, candidate, decision)

    if not should_send_alert(cur, candidate, decision, ttl_minutes):
        return 0

    max_position_value = float(decision.get("max_position_value") or 0.0)
    risk_multiplier = float(decision.get("risk_multiplier") or 0.0)
    entry_price = float(decision.get("entry_price") or 0.0)

    recommended_qty = 0
    if entry_price > 0 and max_position_value > 0:
        recommended_qty = int(max_position_value / entry_price)

    text = (
        "🚨 Торговый ALERT\n\n"
        f"Инструмент: {candidate['symbol']}\n"
        f"Название: {candidate.get('name') or candidate.get('short_name') or 'UNKNOWN'}\n"
        f"Название: {candidate.get('name', 'UNKNOWN')}\n"
        f"Стратегия: {strategy_display_name(candidate['strategy'])}\n"
        f"Режим: {candidate['regime']}\n\n"
        f"Точка входа: {decision['entry_price']}\n"
        f"Стоп-лосс: {decision['stop_loss']}\n"
        f"Тейк-профит: {decision['take_profit']}\n"
        f"Risk/Reward: {decision['risk_reward']}\n\n"
        "Условие входа: покупать только при пробое уровня входа, не по рынку.\n\n"
        f"Максимум позиции: {max_position_value:.2f} ₽\n"
        f"Рекомендуемый объём: {int(decision.get('recommended_qty') or recommended_qty)} шт\n"
        f"Риск на сделку: {float(decision.get('risk_rub') or 0.0):.2f} ₽\n"
        f"Риск на единицу: {float(decision.get('risk_per_unit') or 0.0):.4f} ₽\n"
        f"Капитал в сделке: {float(decision.get('capital_used') or max_position_value):.2f} ₽\n"
        f"Режим разгона: {decision.get('capital_growth_mode', 'N/A')}\n"
        f"Риск от капитала: {float(decision.get('capital_growth_risk_pct') or 0.0) * 100:.2f}%\n"
        f"Множитель риска: {risk_multiplier:.2f}\n"
        f"Вероятность TP: {float(decision.get('probability_tp') or 0.0) * 100:.1f}%\n"
        f"Вероятность SL: {float(decision.get('probability_sl') or 0.0) * 100:.1f}%\n"
        f"Выборка: {int(decision.get('probability_sample_size') or 0)}\n"
        f"Чистый TP: {float(decision.get('net_take_profit') or 0.0):.2f} ₽\n"
        f"Чистый SL: {float(decision.get('net_stop_loss') or 0.0):.2f} ₽\n"
        f"Матожидание: {float(decision.get('expected_value') or 0.0):.2f} ₽ "
        f"({float(decision.get('expected_value_pct') or 0.0):.2f}%)\n"
        f"Качество сделки: {decision.get('trade_quality_grade', 'N/A')} "
        f"({float(decision.get('trade_quality_score') or 0.0):.1f}/100)\n"
        f"Комиссии: {float(decision.get('commissions') or 0.0):.2f} ₽\n"
        f"Налог: {float(decision.get('estimated_tax') or 0.0):.2f} ₽\n\n"
        f"Причина: {decision['reason']}"
    )

    notifier.send(text)
    mark_alert_sent(cur, candidate, decision)
    return 1


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    limit = int(os.getenv("WATCH_RUNTIME_LIMIT", "10"))
    alert_ttl_minutes = int(os.getenv("SIGNAL_ALERT_TTL_MINUTES", "120"))
    max_alerts_per_group = int(os.getenv("MAX_ALERTS_PER_CORRELATION_GROUP", "2"))
    max_active_signals = int(os.getenv("MAX_ACTIVE_SIGNALS", "5"))
    max_active_signals = int(os.getenv("MAX_ACTIVE_SIGNALS", "5"))

    conn = psycopg2.connect(dsn)
    notifier = TelegramNotifier()

    processed = 0
    alerts = 0

    with conn:
        with conn.cursor() as cur:
            candidates = load_watch_candidates(cur, limit=limit)

            for candidate in candidates:
                decision = make_runtime_decision(candidate)
                decision = apply_correlation_filter(
                    cur,
                    candidate,
                    decision,
                    max_alerts_per_group,
                    alert_ttl_minutes,
                )

                if decision.get("decision") == "ALERT":
                    portfolio_decision = PortfolioAwareSignalFilter(conn).check(
                        symbol=candidate["symbol"],
                        max_active_signals=max_active_signals,
                    )

                    if not portfolio_decision.allowed:
                        decision = dict(decision)
                        decision["decision"] = "WATCH"
                        decision["reason"] = f"portfolio_filter: {portfolio_decision.reason}"

                decision = apply_capital_allocator(cur, candidate, decision)
                decision = apply_net_trade_evaluation(cur, candidate, decision)
                decision = apply_trade_quality_score(candidate, decision)
                decision = apply_risk_per_trade_sizing(cur, candidate, decision)

                save_runtime_analysis(cur, candidate, decision)
                alerts += send_alert_if_any(cur, notifier, candidate, decision, alert_ttl_minutes)
                processed += 1

    if alerts == 0 and processed > 0:
        try:
            digest_rows = []

            with conn.cursor() as digest_cur:
                digest_cur.execute(
                    """
                    select
                        symbol,
                        decision,
                        reason
                    from radar_candidate_analysis
                    where source = 'watch_candidate_runtime_analyzer'
                    order by created_at desc, id desc
                    limit 10
                    """
                )

                for r in digest_cur.fetchall():
                    digest_rows.append(
                        {
                            "symbol": r[0],
                            "decision": r[1],
                            "reason": r[2],
                        }
                    )

            notifier.send(build_runtime_digest(digest_rows))

        except Exception as e:
            print(f"RUNTIME_DIGEST_FAILED error={e}", flush=True)

    print(
        f"WATCH_CANDIDATE_RUNTIME_ANALYSIS_OK processed={processed} alerts={alerts}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
