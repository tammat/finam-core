from __future__ import annotations

import json
import os

from finam_core.runtime.runtime_universe_rotation_logger import RuntimeUniverseRotationLogger
from finam_core.storage.postgres_logger import PostgresLogger


LIMIT = int(os.getenv("OPPORTUNITY_WATCHLIST_LIMIT", "5"))
MIN_FRESHNESS_ADJUSTED_SCORE = float(os.getenv("MIN_FRESHNESS_ADJUSTED_SCORE", "0.35"))
FRESHNESS_EXPIRED_SCORE = float(os.getenv("FRESHNESS_EXPIRED_SCORE", "0.25"))
SCORE_DROP_THRESHOLD = float(os.getenv("ROTATION_SCORE_DROP_THRESHOLD", "0.20"))


SQL_SELECT = """
with latest as (
    select distinct on (symbol)
        symbol,
        asset_class,
        atr_pct,
        rvol,
        turnover,
        spread_pct,
        regime,
        smart_money_score,
        smart_money_label,
        trade_priority_score,
        freshness_adjusted_score,
        trade_priority_label,
        trade_priority_reason,
        event_risk_penalty,
        churn_penalty,
        raw,
        calculated_at
    from market_opportunity_metrics
    where is_tradeable = true
      and coalesce(freshness_adjusted_score, trade_priority_score) >= %s
    order by symbol, calculated_at desc
)
select
    symbol,
    asset_class,
    atr_pct,
    rvol,
    turnover,
    spread_pct,
    regime,
    smart_money_score,
    smart_money_label,
    trade_priority_score,
    freshness_adjusted_score,
    trade_priority_label,
    trade_priority_reason,
    event_risk_penalty,
    churn_penalty,
    raw,
    calculated_at
from latest
order by coalesce(freshness_adjusted_score, trade_priority_score) desc, calculated_at desc
limit %s;
"""


def select_strategy(regime: str, score: float) -> str:
    regime_l = str(regime or "").lower()
    if score < MIN_FRESHNESS_ADJUSTED_SCORE:
        return "NO_TRADE"
    if "trend" in regime_l and score >= 0.55:
        return "VOLATILITY_BREAKOUT_EQUITY"
    if "trend" in regime_l:
        return "TREND_PULLBACK_EQUITY"
    return "NO_TRADE"


def classify_rotation_action(previous: dict | None, score: float, strategy: str) -> tuple[str, str | None, str]:
    if score < FRESHNESS_EXPIRED_SCORE:
        return "FRESHNESS_EXPIRED", previous.get("portfolio_status") if previous else None, "WATCH"
    if previous is None:
        return "ADD", None, "ACTIVE"

    previous_score = float(previous.get("score") or 0.0)
    previous_strategy = str(previous.get("strategy") or "")
    previous_status = str(previous.get("portfolio_status") or "WATCH")

    if previous_score > 0 and (previous_score - score) >= SCORE_DROP_THRESHOLD:
        return "SCORE_DROP", previous_status, "ACTIVE"
    if previous_strategy and previous_strategy != strategy:
        return "DOWNGRADE", previous_status, "ACTIVE"
    return "UPDATE", previous_status, "ACTIVE"


def main() -> int:
    pg = PostgresLogger()
    rotation_logger = RuntimeUniverseRotationLogger(pg)

    with pg._connect() as conn:
        with conn.cursor() as cur:
            cur.execute(SQL_SELECT, (MIN_FRESHNESS_ADJUSTED_SCORE, LIMIT))
            rows = cur.fetchall()

            if not rows:
                print("OK: no freshness-adjusted opportunities found")
                return 0

            symbols = [str(row[0]) for row in rows]
            cur.execute(
                """
                select symbol, portfolio_status, strategy, regime, score, reason, raw_json
                from dynamic_watchlist
                where symbol = any(%s)
                """,
                (symbols,),
            )
            previous_by_symbol = {
                str(r[0]): {
                    "portfolio_status": r[1],
                    "strategy": r[2],
                    "regime": r[3],
                    "score": r[4],
                    "reason": r[5],
                    "raw_json": r[6],
                }
                for r in cur.fetchall()
            }

            for row in rows:
                (
                    symbol,
                    asset_class,
                    atr_pct,
                    rvol,
                    turnover,
                    spread_pct,
                    regime,
                    smart_money_score,
                    smart_money_label,
                    trade_priority_score,
                    freshness_adjusted_score,
                    trade_priority_label,
                    trade_priority_reason,
                    event_risk_penalty,
                    churn_penalty,
                    raw,
                    calculated_at,
                ) = row

                base_score = float(trade_priority_score or 0.0)
                score = float(freshness_adjusted_score if freshness_adjusted_score is not None else base_score)
                strategy = select_strategy(str(regime), score)

                raw_payload = {
                    "asset_class": asset_class,
                    "atr_pct": float(atr_pct or 0.0),
                    "rvol": float(rvol or 0.0),
                    "turnover": float(turnover or 0.0),
                    "spread_pct": float(spread_pct or 0.0),
                    "regime": regime,
                    "smart_money_score": float(smart_money_score or 0.0),
                    "smart_money_label": smart_money_label,
                    "trade_priority_score": base_score,
                    "freshness_adjusted_score": score,
                    "trade_priority_label": trade_priority_label,
                    "trade_priority_reason": trade_priority_reason,
                    "event_risk_penalty": float(event_risk_penalty or 0.0),
                    "churn_penalty": float(churn_penalty or 0.0),
                    "strategy": strategy,
                    "source": "freshness_adjusted_scoring_v2",
                    "source_raw": raw,
                    "calculated_at": calculated_at,
                }

                direction = "LONG" if "up" in str(regime).lower() or "trend" in str(regime).lower() else "WATCH"
                reason = (
                    f"trade_priority_score={base_score};"
                    f"freshness_adjusted_score={score};"
                    f"label={trade_priority_label};"
                    f"regime={regime};"
                    f"event_penalty={float(event_risk_penalty or 0.0)};"
                    f"churn_penalty={float(churn_penalty or 0.0)}"
                )

                previous = previous_by_symbol.get(str(symbol))
                rotation_action, previous_status, new_status = classify_rotation_action(previous, score, strategy)

                cur.execute(
                    """
                    insert into dynamic_watchlist (
                        symbol, name, direction, score, relative_strength,
                        portfolio_status, portfolio_action, source,
                        appearances, score_delta, persistence_state,
                        strategy, regime, priority, is_active,
                        reason, raw_json, updated_at
                    )
                    values (
                        %s, %s, %s, %s, %s,
                        %s, %s, 'freshness_adjusted_scoring_v2',
                        1, 0, 'ACTIVE',
                        %s, %s, %s, true,
                        %s, %s::jsonb, now()
                    )
                    on conflict (symbol) do update set
                        ts = now(),
                        direction = excluded.direction,
                        score = excluded.score,
                        relative_strength = excluded.relative_strength,
                        portfolio_status = excluded.portfolio_status,
                        portfolio_action = excluded.portfolio_action,
                        source = excluded.source,
                        appearances = coalesce(dynamic_watchlist.appearances, 0) + 1,
                        score_delta = excluded.score - coalesce(dynamic_watchlist.score, 0),
                        persistence_state = excluded.persistence_state,
                        strategy = excluded.strategy,
                        regime = excluded.regime,
                        priority = excluded.priority,
                        is_active = excluded.is_active,
                        reason = excluded.reason,
                        raw_json = excluded.raw_json,
                        updated_at = now()
                    """,
                    (
                        symbol,
                        symbol,
                        direction,
                        score,
                        float(rvol or 0.0),
                        new_status,
                        f"{strategy};regime={regime};priority={trade_priority_label}",
                        strategy,
                        regime,
                        int(max(1, round(score * 100))),
                        reason,
                        json.dumps(raw_payload, ensure_ascii=False, default=str),
                    ),
                )

                rotation_logger.log_rotation(
                    symbol=str(symbol),
                    action=rotation_action,
                    previous_status=previous_status,
                    new_status=new_status,
                    strategy=strategy,
                    regime=str(regime),
                    score=score,
                    freshness_adjusted_score=score,
                    reason=reason,
                    raw_json=raw_payload,
                )

        conn.commit()

    for row in rows:
        symbol = row[0]
        regime = row[6]
        base_score = float(row[9] or 0.0)
        score = float(row[10] if row[10] is not None else base_score)
        label = row[11]
        print(
            f"FRESHNESS_WATCHLIST symbol={symbol} "
            f"score={score} base_score={base_score} label={label} regime={regime}"
        )

    print(f"OK: dynamic watchlist updated freshness_adjusted_opportunities={len(rows)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
