from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class TradeExitPolicyRepository:
    """
    Русский комментарий:
    Восстанавливает exit policy для закрытых сделок.
    v1 берёт exit_policy из portfolio_governance_events с fallback по symbol/strategy/timeframe.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS trade_exit_policy_context (
            id BIGSERIAL PRIMARY KEY,
            closed_trade_id BIGINT NOT NULL UNIQUE,

            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,

            exit_policy TEXT NOT NULL DEFAULT '',
            exit_reason TEXT NOT NULL DEFAULT '',
            source TEXT NOT NULL DEFAULT 'portfolio_governance_events',

            context_quality TEXT NOT NULL DEFAULT 'PARTIAL',
            missing_fields TEXT NOT NULL DEFAULT '',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_trade_exit_policy_context_symbol
        ON trade_exit_policy_context(symbol);

        CREATE INDEX IF NOT EXISTS idx_trade_exit_policy_context_strategy
        ON trade_exit_policy_context(strategy, timeframe);

        CREATE INDEX IF NOT EXISTS idx_trade_exit_policy_context_quality
        ON trade_exit_policy_context(context_quality);
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build_and_save(self, *, symbol: str, limit: int = 5000) -> tuple[int, int, int]:
        sql = """
        WITH source_trades AS (
            SELECT
                c.id AS closed_trade_id,
                c.symbol,
                COALESCE(c.strategy, '') AS strategy,
                COALESCE(c.timeframe, '') AS timeframe,
                COALESCE(c.trade_source, 'paper') AS trade_source,
                COALESCE(c.exit_ts, c.entry_ts, now()) AS ctx_ts
            FROM closed_trade_chains_v2 c
            WHERE c.symbol = %s
              AND COALESCE(c.strategy, '') <> ''
              AND COALESCE(c.timeframe, '') <> ''
            ORDER BY c.exit_ts DESC NULLS LAST, c.id DESC
            LIMIT %s
        ),
        resolved AS (
            SELECT
                s.*,
                COALESCE(NULLIF(g.exit_policy, ''), 'generic_strategy_exit') AS exit_policy
            FROM source_trades s
            LEFT JOIN LATERAL (
                SELECT
                    exit_policy
                FROM portfolio_governance_events g
                WHERE g.symbol = s.symbol
                  AND COALESCE(g.exit_policy, '') <> ''
                  AND (
                        (g.strategy = s.strategy AND g.timeframe = s.timeframe)
                     OR (g.strategy = s.strategy)
                     OR (COALESCE(g.strategy, '') <> '')
                  )
                ORDER BY
                    CASE
                        WHEN g.strategy = s.strategy AND g.timeframe = s.timeframe THEN 0
                        WHEN g.strategy = s.strategy THEN 1
                        ELSE 2
                    END,
                    CASE
                        WHEN g.created_at <= s.ctx_ts THEN 0
                        ELSE 1
                    END,
                    ABS(EXTRACT(EPOCH FROM (g.created_at - s.ctx_ts))),
                    g.created_at DESC
                LIMIT 1
            ) g ON TRUE
        )
        INSERT INTO trade_exit_policy_context (
            closed_trade_id,
            symbol,
            strategy,
            timeframe,
            trade_source,
            exit_policy,
            exit_reason,
            source,
            context_quality,
            missing_fields,
            updated_at
        )
        SELECT
            closed_trade_id,
            symbol,
            strategy,
            timeframe,
            trade_source,
            exit_policy,
            '' AS exit_reason,
            CASE
                WHEN exit_policy = 'generic_strategy_exit' THEN 'derived_default'
                ELSE 'portfolio_governance_events'
            END AS source,
            CASE
                WHEN exit_policy = 'generic_strategy_exit' THEN 'PARTIAL'
                ELSE 'FULL'
            END AS context_quality,
            CASE
                WHEN exit_policy = 'generic_strategy_exit' THEN 'exit_policy_source'
                ELSE ''
            END AS missing_fields,
            now()
        FROM resolved
        ON CONFLICT (closed_trade_id)
        DO UPDATE SET
            exit_policy = EXCLUDED.exit_policy,
            exit_reason = EXCLUDED.exit_reason,
            source = EXCLUDED.source,
            context_quality = EXCLUDED.context_quality,
            missing_fields = EXCLUDED.missing_fields,
            updated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, limit))

                cur.execute(
                    """
                    SELECT
                        COUNT(*),
                        SUM(CASE WHEN context_quality='FULL' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN context_quality='PARTIAL' THEN 1 ELSE 0 END)
                    FROM trade_exit_policy_context
                    WHERE symbol = %s
                    """,
                    (symbol,),
                )
                row = cur.fetchone()
            conn.commit()

        return int(row[0] or 0), int(row[1] or 0), int(row[2] or 0)
