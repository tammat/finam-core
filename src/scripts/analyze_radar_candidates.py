from __future__ import annotations

import json
import os
import psycopg2


def _as_float(payload: dict, *keys: str, default: float = 0.0) -> float:
    for key in keys:
        try:
            value = payload.get(key)
            if value is not None:
                return float(value)
        except Exception:
            pass
    return default


def decide(row: dict) -> dict:
    symbol = str(row.get("symbol") or "")

    raw = row.get("raw_json") or {}
    if not isinstance(raw, dict):
        raw = {}

    atr_pct = _as_float(raw, "atr_pct")
    rvol = _as_float(raw, "rvol")
    turnover = _as_float(raw, "turnover")
    score = _as_float(raw, "freshness_adjusted_score", "trade_priority_score", "score")
    regime = str(raw.get("regime") or "UNKNOWN")
    strategy = str(raw.get("strategy") or "UNKNOWN")
    source = str(raw.get("source") or "market_radar")

    if not symbol:
        return {
            "decision": "IGNORE",
            "reason": "нет символа",
            "strategy": strategy,
            "regime": regime,
            "score": score,
        }

    # Русский комментарий: если turnover отсутствует, не отсекаем кандидата,
    # потому что ликвидность могла уже быть проверена при формировании dynamic_watchlist.
    if turnover > 0 and turnover < 50_000_000:
        return {
            "decision": "IGNORE",
            "reason": f"низкая ликвидность; turnover={turnover:.0f}",
            "strategy": strategy,
            "regime": regime,
            "score": score,
        }

    # Русский комментарий: отсутствие ATR/RVOL не должно убивать кандидата,
    # если он уже прошёл market radar и имеет положительный score.

    if score <= 0:
        return {
            "decision": "IGNORE",
            "reason": "нулевой приоритет",
            "strategy": strategy,
            "regime": regime,
            "score": score,
        }

    return {
        "decision": "WATCH",
        "reason": (
            f"кандидат для runtime-проверки; "
            f"source={source}; regime={regime}; strategy={strategy}; "
            f"atr_pct={atr_pct:.6f}; rvol={rvol:.4f}; "
            f"turnover={turnover:.0f}; score={score:.6f}"
        ),
        "strategy": strategy,
        "regime": regime,
        "score": score,
    }


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    conn = psycopg2.connect(dsn)

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                select
                    symbol,
                    score,
                    relative_strength,
                    strategy,
                    regime,
                    reason,
                    raw_json
                from dynamic_watchlist
                where is_active = true
                order by updated_at desc
                limit 10
            """)

            rows = []
            for symbol, score, relative_strength, strategy, regime, reason, raw_json in cur.fetchall():
                payload = raw_json or {}
                if not isinstance(payload, dict):
                    payload = {}

                payload["symbol"] = symbol
                payload["score"] = float(score or 0)
                payload["relative_strength"] = float(relative_strength or 0)
                payload["strategy"] = strategy or payload.get("strategy") or "UNKNOWN"
                payload["regime"] = regime or payload.get("regime") or "UNKNOWN"
                payload["reason"] = reason or payload.get("reason") or ""

                rows.append({
                    "symbol": symbol,
                    "raw_json": payload,
                })

            saved = 0
            watch = 0
            ignored = 0

            for row in rows:
                symbol = row["symbol"]
                analysis = decide(row)

                cur.execute("""
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
                    values (
                        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb
                    )
                """, (
                    symbol,
                    "market_radar_top10",
                    analysis.get("decision"),
                    analysis.get("reason"),
                    analysis.get("strategy"),
                    analysis.get("regime"),
                    None,
                    None,
                    None,
                    None,
                    analysis.get("score"),
                    json.dumps(row, ensure_ascii=False, default=str),
                ))

                saved += 1

                if analysis["decision"] == "WATCH":
                    watch += 1
                else:
                    ignored += 1

    print(
        f"RADAR_CANDIDATE_ANALYSIS_OK saved={saved} watch={watch} ignored={ignored} alerts=0",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
