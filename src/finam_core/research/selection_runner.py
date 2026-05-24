from __future__ import annotations

import os

import psycopg


def run_selection_layer_v1() -> None:
    """Русский комментарий: перенос подтвержденных research-связок в selection state."""

    database_url = os.environ["DATABASE_URL"]

    sql = """
    WITH latest_run AS (
        SELECT run_id
        FROM strategy_research_results
        ORDER BY created_at DESC
        LIMIT 1
    ),
    accepted AS (
        SELECT
            r.run_id,
            r.strategy,
            r.symbol,
            r.regime,
            r.trades,
            r.expectancy,
            r.profit_factor,
            r.max_drawdown,
            r.reason
        FROM strategy_research_results r
        JOIN latest_run lr ON lr.run_id = r.run_id
        WHERE r.decision = 'ACCEPT'
    )
    INSERT INTO strategy_selection_state (
        strategy,
        symbol,
        regime,
        status,
        source_run_id,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        reason,
        updated_at
    )
    SELECT
        strategy,
        symbol,
        regime,
        'ENABLED_RESEARCH',
        run_id,
        trades,
        expectancy,
        profit_factor,
        max_drawdown,
        reason,
        now()
    FROM accepted
    ON CONFLICT(strategy, symbol, regime)
    DO UPDATE SET
        status = EXCLUDED.status,
        source_run_id = EXCLUDED.source_run_id,
        trades = EXCLUDED.trades,
        expectancy = EXCLUDED.expectancy,
        profit_factor = EXCLUDED.profit_factor,
        max_drawdown = EXCLUDED.max_drawdown,
        reason = EXCLUDED.reason,
        updated_at = now()
    RETURNING strategy, symbol, regime, status, trades, expectancy, profit_factor, max_drawdown;
    """

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql)
            rows = cur.fetchall()
        conn.commit()

    for row in rows:
        print(
            "SELECTION_STATE_UPSERTED "
            f"strategy={row[0]} "
            f"symbol={row[1]} "
            f"regime={row[2]} "
            f"status={row[3]} "
            f"trades={row[4]} "
            f"expectancy={row[5]} "
            f"profit_factor={row[6]} "
            f"max_drawdown={row[7]}",
            flush=True,
        )

    print(f"SELECTION_LAYER_V1_DONE selected={len(rows)}", flush=True)


if __name__ == "__main__":
    run_selection_layer_v1()
