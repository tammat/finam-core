from __future__ import annotations

import psycopg

from finam_core.runtime.strategy_promotion_feed import StrategyPromotionDecision


class StrategyPromotionFeedRepository:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS strategy_promotion_runtime_feed (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_source TEXT NOT NULL,
            runtime_action TEXT NOT NULL,
            allow_paper_signal BOOLEAN NOT NULL,
            allow_radar_signal BOOLEAN NOT NULL,
            allow_real_suggestion BOOLEAN NOT NULL,
            reason TEXT NOT NULL DEFAULT '',
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE(symbol, strategy, timeframe, trade_source)
        );

        CREATE INDEX IF NOT EXISTS idx_strategy_promotion_feed_symbol
        ON strategy_promotion_runtime_feed(symbol);

        CREATE INDEX IF NOT EXISTS idx_strategy_promotion_feed_action
        ON strategy_promotion_runtime_feed(runtime_action);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save(self, items: list[StrategyPromotionDecision]) -> int:
        sql = """
        INSERT INTO strategy_promotion_runtime_feed (
            symbol,
            strategy,
            timeframe,
            trade_source,
            runtime_action,
            allow_paper_signal,
            allow_radar_signal,
            allow_real_suggestion,
            reason,
            updated_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,now())
        ON CONFLICT (symbol, strategy, timeframe, trade_source)
        DO UPDATE SET
            runtime_action = EXCLUDED.runtime_action,
            allow_paper_signal = EXCLUDED.allow_paper_signal,
            allow_radar_signal = EXCLUDED.allow_radar_signal,
            allow_real_suggestion = EXCLUDED.allow_real_suggestion,
            reason = EXCLUDED.reason,
            updated_at = now()
        """

        saved = 0

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in items:
                    cur.execute(
                        sql,
                        (
                            item.symbol,
                            item.strategy,
                            item.timeframe,
                            item.trade_source,
                            item.runtime_action,
                            item.allow_paper_signal,
                            item.allow_radar_signal,
                            item.allow_real_suggestion,
                            item.reason,
                        ),
                    )
                    saved += cur.rowcount
            conn.commit()

        return saved
