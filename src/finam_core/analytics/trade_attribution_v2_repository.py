from __future__ import annotations

import psycopg

from finam_core.analytics.trade_attribution_v2 import (
    TradeAttributionV2,
    classify_trade_attribution_quality,
)


class TradeAttributionV2Repository:
    """
    Русский комментарий:
    Обогащает closed_trade_chains_v2 контекстом governance / lifecycle / exit policy.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS trade_attribution_v2 (
            id BIGSERIAL PRIMARY KEY,
            closed_trade_id BIGINT NOT NULL UNIQUE,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL DEFAULT '',
            timeframe TEXT NOT NULL DEFAULT '',
            trade_source TEXT NOT NULL DEFAULT '',
            pnl NUMERIC NOT NULL DEFAULT 0,
            side TEXT NOT NULL DEFAULT '',
            regime TEXT NOT NULL DEFAULT 'unknown',
            heat_status TEXT NOT NULL DEFAULT 'unknown',
            risk_multiplier NUMERIC NOT NULL DEFAULT 1,
            lifecycle_action TEXT NOT NULL DEFAULT 'NO_ACTION',
            exit_policy TEXT NOT NULL DEFAULT '',
            attribution_quality TEXT NOT NULL DEFAULT '',
            reason TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_trade_attribution_v2_symbol
        ON trade_attribution_v2(symbol, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_trade_attribution_v2_strategy
        ON trade_attribution_v2(strategy, timeframe, created_at DESC);

        CREATE INDEX IF NOT EXISTS idx_trade_attribution_v2_quality
        ON trade_attribution_v2(attribution_quality);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build(self, *, symbol: str, limit: int = 1000) -> list[TradeAttributionV2]:
        sql = """
        SELECT
            c.id,
            c.symbol,
            c.strategy,
            c.timeframe,
            c.trade_source,
            c.pnl,
            c.side,

            COALESCE(g.portfolio_heat_status, 'unknown') AS heat_status,
            COALESCE(g.portfolio_risk_multiplier, 1) AS risk_multiplier,
            COALESCE(g.exit_policy, '') AS exit_policy,

            COALESCE(l.action, 'NO_ACTION') AS lifecycle_action,

            'unknown' AS regime

        FROM closed_trade_chains_v2 c

        LEFT JOIN LATERAL (
            SELECT
                portfolio_heat_status,
                portfolio_risk_multiplier,
                exit_policy
            FROM portfolio_governance_events g
            WHERE g.symbol = c.symbol
              AND g.strategy = c.strategy
              AND g.timeframe = c.timeframe
              AND g.created_at <= c.exit_ts
            ORDER BY g.created_at DESC
            LIMIT 1
        ) g ON TRUE

        LEFT JOIN LATERAL (
            SELECT action
            FROM lifecycle_stale_position_advice_events l
            WHERE l.symbol = c.symbol
              AND l.created_at <= c.exit_ts
            ORDER BY l.created_at DESC
            LIMIT 1
        ) l ON TRUE

        WHERE c.symbol = %s
        ORDER BY c.exit_ts DESC, c.id DESC
        LIMIT %s
        """

        result: list[TradeAttributionV2] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, limit))
                rows = cur.fetchall()

        for row in rows:
            quality, reason = classify_trade_attribution_quality(
                strategy=str(row[2] or ""),
                timeframe=str(row[3] or ""),
                heat_status=str(row[7] or "unknown"),
                lifecycle_action=str(row[10] or "NO_ACTION"),
                exit_policy=str(row[9] or ""),
            )

            result.append(
                TradeAttributionV2(
                    closed_trade_id=int(row[0]),
                    symbol=str(row[1]),
                    strategy=str(row[2] or ""),
                    timeframe=str(row[3] or ""),
                    trade_source=str(row[4] or ""),
                    pnl=float(row[5] or 0.0),
                    side=str(row[6] or ""),
                    heat_status=str(row[7] or "unknown"),
                    risk_multiplier=float(row[8] or 1.0),
                    exit_policy=str(row[9] or ""),
                    lifecycle_action=str(row[10] or "NO_ACTION"),
                    regime=str(row[11] or "unknown"),
                    attribution_quality=quality,
                    reason=reason,
                )
            )

        return result

    def save(self, items: list[TradeAttributionV2]) -> int:
        sql = """
        INSERT INTO trade_attribution_v2 (
            closed_trade_id,
            symbol,
            strategy,
            timeframe,
            trade_source,
            pnl,
            side,
            regime,
            heat_status,
            risk_multiplier,
            lifecycle_action,
            exit_policy,
            attribution_quality,
            reason
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
        ON CONFLICT (closed_trade_id)
        DO UPDATE SET
            symbol = EXCLUDED.symbol,
            strategy = EXCLUDED.strategy,
            timeframe = EXCLUDED.timeframe,
            trade_source = EXCLUDED.trade_source,
            pnl = EXCLUDED.pnl,
            side = EXCLUDED.side,
            regime = EXCLUDED.regime,
            heat_status = EXCLUDED.heat_status,
            risk_multiplier = EXCLUDED.risk_multiplier,
            lifecycle_action = EXCLUDED.lifecycle_action,
            exit_policy = EXCLUDED.exit_policy,
            attribution_quality = EXCLUDED.attribution_quality,
            reason = EXCLUDED.reason
        """

        saved = 0

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(
                        sql,
                        (
                            item.closed_trade_id,
                            item.symbol,
                            item.strategy,
                            item.timeframe,
                            item.trade_source,
                            item.pnl,
                            item.side,
                            item.regime,
                            item.heat_status,
                            item.risk_multiplier,
                            item.lifecycle_action,
                            item.exit_policy,
                            item.attribution_quality,
                            item.reason,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved
