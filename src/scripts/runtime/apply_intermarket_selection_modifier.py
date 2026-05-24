from __future__ import annotations

import os

import psycopg

from finam_core.runtime.intermarket_selection_modifier import build_intermarket_modifier


def main() -> None:
    """
    Русский комментарий:
    Применяет последний intermarket_regime_snapshot к runtime_strategy_scores.

    Важно:
    - не меняет strategy_selection_state;
    - не включает PROMOTED_RUNTIME;
    - только добавляет скорректированные score-записи.
    """
    database_url = os.environ["DATABASE_URL"]

    latest_regime_sql = """
    SELECT
        risk_mode,
        commodity_mode,
        confidence,
        commodity_score,
        fx_stress_score
    FROM intermarket_regime_snapshots
    ORDER BY ts DESC
    LIMIT 1;
    """

    latest_scores_sql = """
    SELECT
        strategy,
        root_symbol,
        regime,
        score,
        confidence,
        recommendation,
        source_status,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        reason
    FROM runtime_strategy_scores_latest;
    """

    insert_sql = """
    INSERT INTO runtime_strategy_scores (
        strategy,
        root_symbol,
        regime,
        score,
        confidence,
        recommendation,
        source_status,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        reason
    )
    VALUES (
        %(strategy)s,
        %(root_symbol)s,
        %(regime)s,
        %(score)s,
        %(confidence)s,
        %(recommendation)s,
        %(source_status)s,
        %(trades)s,
        %(expectancy)s,
        %(profit_factor)s,
        %(max_drawdown)s,
        %(reason)s
    );
    """

    updated = 0

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(latest_regime_sql)
            regime_row = cur.fetchone()

            if regime_row is None:
                print("INTERMARKET_SELECTION_MODIFIER_SKIPPED reason=no_intermarket_snapshot", flush=True)
                return

            risk_mode, commodity_mode, im_confidence, commodity_score, fx_stress_score = regime_row

            cur.execute(latest_scores_sql)
            score_rows = cur.fetchall()

            for row in score_rows:
                (
                    strategy,
                    root_symbol,
                    regime,
                    score,
                    base_confidence,
                    recommendation,
                    source_status,
                    trades,
                    expectancy,
                    profit_factor,
                    max_drawdown,
                    reason,
                ) = row

                modifier = build_intermarket_modifier(
                    strategy=str(strategy),
                    root_symbol=str(root_symbol),
                    risk_mode=str(risk_mode),
                    commodity_mode=str(commodity_mode),
                    confidence=float(im_confidence),
                    commodity_score=float(commodity_score),
                    fx_stress_score=float(fx_stress_score),
                )

                new_score = max(0.0, min(1.0, float(score) * modifier.score_multiplier))
                new_confidence = max(0.0, min(1.0, float(base_confidence) + modifier.confidence_delta))

                cur.execute(
                    insert_sql,
                    {
                        "strategy": strategy,
                        "root_symbol": root_symbol,
                        "regime": regime,
                        "score": new_score,
                        "confidence": new_confidence,
                        "recommendation": f"{recommendation}|{modifier.recommendation_suffix}",
                        "source_status": source_status,
                        "trades": trades,
                        "expectancy": expectancy,
                        "profit_factor": profit_factor,
                        "max_drawdown": max_drawdown,
                        "reason": f"{reason} | intermarket_modifier:{modifier.reason}",
                    },
                )
                updated += 1

        conn.commit()

    print(
        "INTERMARKET_SELECTION_MODIFIER_OK "
        f"updated={updated} risk_mode={risk_mode} commodity_mode={commodity_mode}",
        flush=True,
    )


if __name__ == "__main__":
    main()
