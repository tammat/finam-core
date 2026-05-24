from __future__ import annotations

import os

import psycopg

from finam_core.runtime.context_runtime_filter import build_context_runtime_decision


def main() -> None:
    database_url = os.environ["DATABASE_URL"]

    sql = """
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
            rs.trades AS score_trades,
            rs.expectancy AS score_expectancy,
            rs.profit_factor AS score_profit_factor,
            rs.max_drawdown,
            rs.reason AS score_reason,

            srp.status AS context_status,
            srp.trades AS context_trades,
            srp.profit_factor AS context_profit_factor,
            srp.expectancy AS context_expectancy
        FROM latest_scores rs
        JOIN latest_feature lf
          ON lf.root_symbol = rs.root_symbol
        LEFT JOIN strategy_regime_performance srp
          ON srp.strategy = rs.strategy
         AND srp.symbol LIKE rs.root_symbol || '%%'
         AND srp.regime = lf.regime
         AND srp.trend = lf.trend
         AND srp.volatility = lf.volatility
    )
    SELECT
        strategy,
        root_symbol,
        score_regime,
        score,
        confidence,
        recommendation,
        source_status,
        score_trades,
        score_expectancy,
        score_profit_factor,
        max_drawdown,
        score_reason,
        COALESCE(context_status, 'LOW_SAMPLE') AS context_status,
        COALESCE(context_trades, 0) AS context_trades,
        COALESCE(context_profit_factor, 0) AS context_profit_factor,
        COALESCE(context_expectancy, 0) AS context_expectancy
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
            cur.execute(sql)
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
                    score_trades,
                    score_expectancy,
                    score_profit_factor,
                    max_drawdown,
                    score_reason,
                    context_status,
                    context_trades,
                    context_profit_factor,
                    context_expectancy,
                ) = row

                decision = build_context_runtime_decision(
                    context_status=str(context_status),
                    trades=int(context_trades or 0),
                    profit_factor=float(context_profit_factor or 0),
                    expectancy=float(context_expectancy or 0),
                )

                new_score = max(0.0, min(1.0, float(score) * decision.score_multiplier))
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
                        "trades": score_trades,
                        "expectancy": score_expectancy,
                        "profit_factor": score_profit_factor,
                        "max_drawdown": max_drawdown,
                        "reason": f"{score_reason} | context_runtime_filter:{decision.reason}",
                    },
                )
                updated += 1

        conn.commit()

    print(f"CONTEXT_RUNTIME_FILTER_OK updated={updated}", flush=True)


if __name__ == "__main__":
    main()
