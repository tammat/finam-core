from __future__ import annotations

import os

import psycopg

from finam_core.runtime.regime_matrix_modifier import (
    build_regime_matrix_runtime_decision,
)


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    select_sql = """
    WITH latest_feature AS (
        SELECT DISTINCT ON (root_symbol)
            root_symbol,
            intermarket_commodity_mode AS regime,
            trend_state AS trend,
            volatility_state AS volatility
        FROM feature_snapshots
        ORDER BY root_symbol, ts DESC
    ),
    latest_scores AS (
        SELECT *
        FROM runtime_strategy_scores_latest
    ),
    matched AS (
        SELECT
            rs.strategy,
            rs.root_symbol,
            rs.regime AS score_regime,
            rs.score,
            rs.confidence,
            rs.recommendation,
            rs.source_status,
            rs.trades,
            rs.expectancy,
            rs.profit_factor,
            rs.max_drawdown,
            rs.reason AS score_reason,

            srm.runtime_action,
            srm.score_adjustment,
            srm.confidence_adjustment,
            srm.reason AS matrix_reason
        FROM latest_scores rs
        JOIN latest_feature lf
          ON lf.root_symbol = rs.root_symbol
        LEFT JOIN strategy_regime_matrix srm
          ON srm.strategy = rs.strategy
         AND srm.timeframe = rs.regime
         AND srm.regime = lf.regime
         AND srm.trend = lf.trend
         AND srm.volatility = lf.volatility
    )
    SELECT
        strategy,
        root_symbol,
        score_regime,
        score,
        confidence,
        recommendation,
        source_status,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        score_reason,
        COALESCE(runtime_action, 'UNKNOWN') AS runtime_action,
        COALESCE(score_adjustment, 0) AS score_adjustment,
        COALESCE(confidence_adjustment, 0) AS confidence_adjustment,
        COALESCE(matrix_reason, 'no_regime_matrix_match') AS matrix_reason
    FROM matched;
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
            cur.execute(select_sql)
            rows = cur.fetchall()

            for row in rows:
                (
                    strategy,
                    root_symbol,
                    score_regime,
                    score,
                    confidence,
                    recommendation,
                    source_status,
                    trades,
                    expectancy,
                    profit_factor,
                    max_drawdown,
                    score_reason,
                    runtime_action,
                    score_adjustment,
                    confidence_adjustment,
                    matrix_reason,
                ) = row

                decision = build_regime_matrix_runtime_decision(
                    runtime_action=str(runtime_action),
                    score_adjustment=float(score_adjustment or 0),
                    confidence_adjustment=float(confidence_adjustment or 0),
                )

                new_score = max(0.0, min(1.0, float(score) + decision.score_delta))
                new_confidence = max(0.0, min(1.0, float(confidence) + decision.confidence_delta))

                cur.execute(
                    insert_sql,
                    {
                        "strategy": strategy,
                        "root_symbol": root_symbol,
                        "regime": score_regime,
                        "score": new_score,
                        "confidence": new_confidence,
                        "recommendation": f"{recommendation}|{decision.suffix}",
                        "source_status": source_status,
                        "trades": trades,
                        "expectancy": expectancy,
                        "profit_factor": profit_factor,
                        "max_drawdown": max_drawdown,
                        "reason": (
                            f"{score_reason} | "
                            f"regime_matrix_modifier:{decision.reason};{matrix_reason}"
                        ),
                    },
                )
                updated += 1

        conn.commit()

    print(f"REGIME_MATRIX_RUNTIME_MODIFIER_OK updated={updated}", flush=True)


if __name__ == "__main__":
    main()
