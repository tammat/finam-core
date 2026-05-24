from __future__ import annotations

import os

import psycopg

from finam_core.runtime.regime_runtime_override import build_regime_runtime_override


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    select_sql = """
    SELECT
        strategy,
        root_symbol,
        regime,
        score,
        confidence,
        recommendation
    FROM runtime_strategy_scores_latest;
    """

    insert_sql = """
    INSERT INTO runtime_regime_overrides (
        strategy,
        root_symbol,
        regime,
        runtime_action,
        max_position_size,
        allowed_execution_mode,
        risk_multiplier,
        cooldown_sec,
        stop_take_profile,
        source_recommendation,
        reason,
        is_default_policy
    )
    VALUES (
        %(strategy)s,
        %(root_symbol)s,
        %(regime)s,
        %(runtime_action)s,
        %(max_position_size)s,
        %(allowed_execution_mode)s,
        %(risk_multiplier)s,
        %(cooldown_sec)s,
        %(stop_take_profile)s,
        %(source_recommendation)s,
        %(reason)s,
        %(is_default_policy)s
    )
    ON CONFLICT (strategy, root_symbol, regime)
    DO UPDATE SET
        runtime_action = EXCLUDED.runtime_action,
        max_position_size = EXCLUDED.max_position_size,
        allowed_execution_mode = EXCLUDED.allowed_execution_mode,
        risk_multiplier = EXCLUDED.risk_multiplier,
        cooldown_sec = EXCLUDED.cooldown_sec,
        stop_take_profile = EXCLUDED.stop_take_profile,
        source_recommendation = EXCLUDED.source_recommendation,
        reason = EXCLUDED.reason,
        is_default_policy = EXCLUDED.is_default_policy,
        created_at = now();
    """

    saved = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(select_sql)
            rows = cur.fetchall()

            for row in rows:
                strategy, root_symbol, regime, score, confidence, recommendation = row

                override = build_regime_runtime_override(
                    recommendation=str(recommendation or ""),
                    score=float(score or 0),
                    confidence=float(confidence or 0),
                )

                cur.execute(
                    insert_sql,
                    {
                        "strategy": strategy,
                        "root_symbol": root_symbol,
                        "regime": regime,
                        "runtime_action": override.runtime_action,
                        "max_position_size": override.max_position_size,
                        "allowed_execution_mode": override.allowed_execution_mode,
                        "risk_multiplier": override.risk_multiplier,
                        "cooldown_sec": override.cooldown_sec,
                        "stop_take_profile": override.stop_take_profile,
                        "source_recommendation": recommendation,
                        "reason": override.reason,
                        "is_default_policy": override.runtime_action == "NEUTRAL",
                    },
                )
                saved += 1

        conn.commit()

    print(f"RUNTIME_REGIME_OVERRIDES_V3_OK saved={saved}", flush=True)


if __name__ == "__main__":
    main()
