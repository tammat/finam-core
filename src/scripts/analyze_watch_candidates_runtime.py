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

    text = (
        "🚨 Торговый ALERT\n\n"
        f"Инструмент: {candidate['symbol']}\n"
        f"Стратегия: {candidate['strategy']}\n"
        f"Режим: {candidate['regime']}\n\n"
        f"Точка входа: {decision['entry_price']}\n"
        f"Стоп-лосс: {decision['stop_loss']}\n"
        f"Тейк-профит: {decision['take_profit']}\n"
        f"Risk/Reward: {decision['risk_reward']}\n\n"
        "Условие входа: покупать только при пробое уровня входа, не по рынку.\n\n"
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
