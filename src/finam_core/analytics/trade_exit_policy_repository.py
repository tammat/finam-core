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
            governance_event_id BIGINT,

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
        ALTER TABLE trade_exit_policy_context
            ADD COLUMN IF NOT EXISTS governance_event_id BIGINT;

        CREATE TABLE IF NOT EXISTS analytics.trade_context_quarantine_v1 (
            closed_trade_id BIGINT NOT NULL,
            context_type TEXT NOT NULL,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL DEFAULT '',
            timeframe TEXT NOT NULL DEFAULT '',
            reason_code TEXT NOT NULL,
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            first_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            last_seen_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ,
            PRIMARY KEY (closed_trade_id, context_type)
        );
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
                COALESCE(NULLIF(g.exit_policy, ''), 'generic_strategy_exit') AS exit_policy,
                g.governance_event_id
            FROM source_trades s
            LEFT JOIN LATERAL (
                SELECT
                    id AS governance_event_id,
                    exit_policy
                FROM portfolio_governance_events g
                WHERE g.symbol = s.symbol
                  AND COALESCE(g.exit_policy, '') <> ''
                  AND g.strategy = s.strategy
                  AND g.timeframe = s.timeframe
                  AND g.created_at <= s.ctx_ts
                ORDER BY g.created_at DESC
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
            governance_event_id,
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
            governance_event_id,
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
            governance_event_id = EXCLUDED.governance_event_id,
            context_quality = EXCLUDED.context_quality,
            missing_fields = EXCLUDED.missing_fields,
            updated_at = now()
        """

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, limit))
                cur.execute(
                    """
                    INSERT INTO analytics.trade_context_quarantine_v1 (
                        closed_trade_id, context_type, symbol, strategy, timeframe,
                        reason_code, details, last_seen_at, resolved_at
                    )
                    SELECT closed_trade_id, 'exit_policy', symbol, strategy, timeframe,
                           'NO_EXACT_PRE_EXIT_POLICY_EVENT',
                           jsonb_build_object('trade_source', trade_source), now(), NULL
                    FROM trade_exit_policy_context
                    WHERE symbol=%s AND context_quality='PARTIAL'
                    ON CONFLICT (closed_trade_id, context_type) DO UPDATE SET
                        reason_code=EXCLUDED.reason_code, details=EXCLUDED.details,
                        last_seen_at=now(), resolved_at=NULL
                    """,
                    (symbol,),
                )
                cur.execute(
                    """
                    UPDATE analytics.trade_context_quarantine_v1 q
                    SET resolved_at=now(), last_seen_at=now()
                    FROM trade_exit_policy_context e
                    WHERE q.closed_trade_id=e.closed_trade_id
                      AND q.context_type='exit_policy'
                      AND e.symbol=%s AND e.context_quality='FULL'
                    """,
                    (symbol,),
                )

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
