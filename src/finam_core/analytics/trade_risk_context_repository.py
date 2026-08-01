from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


class TradeRiskContextRepository:
    """
    Русский комментарий:
    Строит риск-контекст закрытых сделок на основе portfolio governance events.
    v1 берёт ближайший portfolio/risk event по symbol + strategy + timeframe.
    """

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS trade_risk_context (
            id BIGSERIAL PRIMARY KEY,
            closed_trade_id BIGINT NOT NULL UNIQUE,

            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,

            heat_status TEXT NOT NULL DEFAULT 'unknown',
            risk_multiplier NUMERIC NOT NULL DEFAULT 1.0,
            allow_new_entries BOOLEAN,
            governance_mode TEXT NOT NULL DEFAULT 'unknown',
            governance_reason TEXT NOT NULL DEFAULT '',

            context_quality TEXT NOT NULL DEFAULT 'PARTIAL',
            missing_fields TEXT NOT NULL DEFAULT '',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_trade_risk_context_symbol
        ON trade_risk_context(symbol);

        CREATE INDEX IF NOT EXISTS idx_trade_risk_context_strategy
        ON trade_risk_context(strategy, timeframe);

        CREATE INDEX IF NOT EXISTS idx_trade_risk_context_quality
        ON trade_risk_context(context_quality);

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
                COALESCE(c.entry_ts, c.exit_ts, now()) AS ctx_ts
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
                COALESCE(g.heat_status, 'unknown') AS heat_status,
                COALESCE(g.risk_multiplier, 1.0) AS risk_multiplier,
                g.allow_new_entries,
                COALESCE(g.mode, 'unknown') AS governance_mode,
                COALESCE(g.reason, '') AS governance_reason
            FROM source_trades s
            LEFT JOIN LATERAL (
                SELECT
                    g.portfolio_heat_status AS heat_status,
                    g.portfolio_risk_multiplier AS risk_multiplier,
                    g.allow_new_entries,
                    g.governance_mode AS mode,
                    COALESCE(g.exit_policy, '') AS reason
                FROM portfolio_governance_events g
                WHERE g.symbol = s.symbol
                  AND g.strategy = s.strategy
                  AND g.timeframe = s.timeframe
                  AND g.created_at <= s.ctx_ts
                ORDER BY g.created_at DESC
                LIMIT 1
            ) g ON TRUE
        )
        INSERT INTO trade_risk_context (
            closed_trade_id,
            symbol,
            strategy,
            timeframe,
            trade_source,
            heat_status,
            risk_multiplier,
            allow_new_entries,
            governance_mode,
            governance_reason,
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
            heat_status,
            risk_multiplier,
            allow_new_entries,
            governance_mode,
            governance_reason,
            CASE
                WHEN heat_status = 'unknown' THEN 'PARTIAL'
                ELSE 'FULL'
            END AS context_quality,
            CASE
                WHEN heat_status = 'unknown' THEN 'heat_status'
                ELSE ''
            END AS missing_fields,
            now()
        FROM resolved
        ON CONFLICT (closed_trade_id)
        DO UPDATE SET
            heat_status = EXCLUDED.heat_status,
            risk_multiplier = EXCLUDED.risk_multiplier,
            allow_new_entries = EXCLUDED.allow_new_entries,
            governance_mode = EXCLUDED.governance_mode,
            governance_reason = EXCLUDED.governance_reason,
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
                    SELECT closed_trade_id, 'heat_status', symbol, strategy, timeframe,
                           'NO_EXACT_PRE_TRADE_GOVERNANCE_EVENT',
                           jsonb_build_object('trade_source', trade_source), now(), NULL
                    FROM trade_risk_context
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
                    FROM trade_risk_context r
                    WHERE q.closed_trade_id=r.closed_trade_id
                      AND q.context_type='heat_status'
                      AND r.symbol=%s AND r.context_quality='FULL'
                    """,
                    (symbol,),
                )
                saved = cur.rowcount

                cur.execute(
                    """
                    SELECT
                        COUNT(*),
                        SUM(CASE WHEN context_quality='FULL' THEN 1 ELSE 0 END),
                        SUM(CASE WHEN context_quality='PARTIAL' THEN 1 ELSE 0 END)
                    FROM trade_risk_context
                    WHERE symbol = %s
                    """,
                    (symbol,),
                )
                row = cur.fetchone()
            conn.commit()

        total = int(row[0] or 0)
        full = int(row[1] or 0)
        partial = int(row[2] or 0)

        return total, full, partial
