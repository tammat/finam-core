from __future__ import annotations

import psycopg

from finam_core.analytics.trade_context_snapshot import TradeContextSnapshot


# TODO v2:
# Подключить реальные источники контекста:
# - regime/trend/volatility из regime-layer или market feature snapshots;
# - signal_score/risk_reward из сохранённых signal/features;
# - heat_status/risk_multiplier из portfolio governance events;
# - exit_policy из exit policy / protective order lifecycle.
# Сейчас v1 намеренно фиксирует неполный контекст как PARTIAL.

class TradeContextSnapshotRepository:
    """
    Русский комментарий:
    Сохраняет контекст закрытой сделки.
    Это объяснительный слой: почему стратегия заработала или не заработала.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS trade_context_snapshots (
            id BIGSERIAL PRIMARY KEY,
            closed_trade_id BIGINT NOT NULL UNIQUE,

            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,

            entry_ts TIMESTAMPTZ,
            exit_ts TIMESTAMPTZ,

            regime TEXT NOT NULL DEFAULT 'unknown',
            trend TEXT NOT NULL DEFAULT 'unknown',
            volatility TEXT NOT NULL DEFAULT 'unknown',

            heat_status TEXT NOT NULL DEFAULT 'unknown',
            portfolio_risk_multiplier NUMERIC NOT NULL DEFAULT 1.0,

            exit_policy TEXT NOT NULL DEFAULT '',
            lifecycle_state TEXT NOT NULL DEFAULT 'UNKNOWN',

            signal_score NUMERIC NOT NULL DEFAULT 0,
            risk_reward NUMERIC NOT NULL DEFAULT 0,

            context_quality TEXT NOT NULL DEFAULT 'PARTIAL',
            missing_fields TEXT NOT NULL DEFAULT '',

            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_symbol
        ON trade_context_snapshots(symbol);

        CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_strategy
        ON trade_context_snapshots(strategy, timeframe);

        CREATE INDEX IF NOT EXISTS idx_trade_context_snapshots_quality
        ON trade_context_snapshots(context_quality);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def build(self, *, symbol: str, limit: int = 5000) -> list[TradeContextSnapshot]:
        sql = """
        SELECT
            c.id AS closed_trade_id,
            c.symbol,
            COALESCE(c.strategy, '') AS strategy,
            COALESCE(c.timeframe, '') AS timeframe,
            COALESCE(c.trade_source, 'paper') AS trade_source,
            c.entry_ts,
            c.exit_ts,

            'unknown' AS regime,
            'unknown' AS trend,
            'unknown' AS volatility,

            COALESCE(a.heat_status, 'unknown') AS heat_status,
            COALESCE(a.risk_multiplier, 1.0) AS portfolio_risk_multiplier,

            COALESCE(a.exit_policy, '') AS exit_policy,
            COALESCE(l.lifecycle_state, 'UNKNOWN') AS lifecycle_state,

            0 AS signal_score,
            0 AS risk_reward

        FROM closed_trade_chains_v2 c
        LEFT JOIN trade_attribution_v2 a
          ON a.closed_trade_id = c.id
        LEFT JOIN strategy_lifecycle_state l
          ON l.symbol = c.symbol
         AND l.strategy = c.strategy
         AND l.timeframe = c.timeframe
        WHERE c.symbol = %s
          AND COALESCE(c.strategy, '') <> ''
          AND COALESCE(c.timeframe, '') <> ''
        ORDER BY c.exit_ts DESC NULLS LAST, c.id DESC
        LIMIT %s
        """

        items: list[TradeContextSnapshot] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, limit))
                rows = cur.fetchall()

        for row in rows:
            missing = []

            if row[7] == "unknown":
                missing.append("regime")
            if row[8] == "unknown":
                missing.append("trend")
            if row[9] == "unknown":
                missing.append("volatility")
            if row[10] == "unknown":
                missing.append("heat_status")
            if not row[12]:
                missing.append("exit_policy")
            if row[13] == "UNKNOWN":
                missing.append("lifecycle_state")

            quality = "FULL" if not missing else "PARTIAL"

            items.append(
                TradeContextSnapshot(
                    closed_trade_id=int(row[0]),
                    symbol=str(row[1]),
                    strategy=str(row[2]),
                    timeframe=str(row[3]),
                    trade_source=str(row[4]),
                    entry_ts=row[5],
                    exit_ts=row[6],
                    regime=str(row[7]),
                    trend=str(row[8]),
                    volatility=str(row[9]),
                    heat_status=str(row[10]),
                    portfolio_risk_multiplier=float(row[11] or 1.0),
                    exit_policy=str(row[12] or ""),
                    lifecycle_state=str(row[13] or "UNKNOWN"),
                    signal_score=float(row[14] or 0.0),
                    risk_reward=float(row[15] or 0.0),
                    context_quality=quality,
                    missing_fields=",".join(missing),
                )
            )

        return items

    def save(self, items: list[TradeContextSnapshot]) -> int:
        sql = """
        INSERT INTO trade_context_snapshots (
            closed_trade_id,
            symbol,
            strategy,
            timeframe,
            trade_source,
            entry_ts,
            exit_ts,
            regime,
            trend,
            volatility,
            heat_status,
            portfolio_risk_multiplier,
            exit_policy,
            lifecycle_state,
            signal_score,
            risk_reward,
            context_quality,
            missing_fields,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (closed_trade_id)
        DO UPDATE SET
            regime = EXCLUDED.regime,
            trend = EXCLUDED.trend,
            volatility = EXCLUDED.volatility,
            heat_status = EXCLUDED.heat_status,
            portfolio_risk_multiplier = EXCLUDED.portfolio_risk_multiplier,
            exit_policy = EXCLUDED.exit_policy,
            lifecycle_state = EXCLUDED.lifecycle_state,
            signal_score = EXCLUDED.signal_score,
            risk_reward = EXCLUDED.risk_reward,
            context_quality = EXCLUDED.context_quality,
            missing_fields = EXCLUDED.missing_fields,
            updated_at = now()
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
                            item.entry_ts,
                            item.exit_ts,
                            item.regime,
                            item.trend,
                            item.volatility,
                            item.heat_status,
                            item.portfolio_risk_multiplier,
                            item.exit_policy,
                            item.lifecycle_state,
                            item.signal_score,
                            item.risk_reward,
                            item.context_quality,
                            item.missing_fields,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved
