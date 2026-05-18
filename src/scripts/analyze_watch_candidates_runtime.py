from __future__ import annotations

import json
import os
import psycopg2
from datetime import datetime, timezone

from finam_core.notifications.telegram_notifier import TelegramNotifier


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


def make_runtime_decision(candidate: dict) -> dict:
    """
    Русский комментарий:
    v1 не имитирует реальную цену и не отправляет ложный торговый сигнал.
    Он только подтверждает, что кандидат готов к runtime-проверке.
    Настоящие entry/stop/take появятся после подключения price/strategy engine.
    """
    score = float(candidate.get("score") or 0.0)
    strategy = str(candidate.get("strategy") or "UNKNOWN")
    regime = str(candidate.get("regime") or "UNKNOWN")

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

    return {
        "decision": "WATCH",
        "reason": f"кандидат ожидает подтверждения цены и стратегии; strategy={strategy}; regime={regime}; score={score:.6f}",
        "entry_price": None,
        "stop_loss": None,
        "take_profit": None,
        "risk_reward": None,
    }


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


def send_alert_if_any(notifier: TelegramNotifier, candidate: dict, decision: dict) -> int:
    if decision["decision"] != "ALERT":
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
        f"Причина: {decision['reason']}"
    )

    notifier.send(text)
    return 1


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    limit = int(os.getenv("WATCH_RUNTIME_LIMIT", "10"))

    conn = psycopg2.connect(dsn)
    notifier = TelegramNotifier()

    processed = 0
    alerts = 0

    with conn:
        with conn.cursor() as cur:
            candidates = load_watch_candidates(cur, limit=limit)

            for candidate in candidates:
                decision = make_runtime_decision(candidate)
                save_runtime_analysis(cur, candidate, decision)
                alerts += send_alert_if_any(notifier, candidate, decision)
                processed += 1

    print(
        f"WATCH_CANDIDATE_RUNTIME_ANALYSIS_OK processed={processed} alerts={alerts}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
