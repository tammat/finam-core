from __future__ import annotations

import psycopg


class BrokerManualTradeSync:
    """
    Русский комментарий:
    Синхронизирует ручные сделки только из брокерских фактических событий.
    Ручной ввод сделок запрещён.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS manual_trade_journal (
            id BIGSERIAL PRIMARY KEY,
            broker_event_id TEXT UNIQUE,
            ts TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            display_name TEXT NOT NULL DEFAULT '',
            side TEXT NOT NULL,
            qty NUMERIC NOT NULL,
            price NUMERIC NOT NULL,
            source TEXT NOT NULL DEFAULT 'BROKER',
            trade_mode TEXT NOT NULL DEFAULT 'REAL_MANUAL_BROKER',
            strategy_reference TEXT NOT NULL DEFAULT '',
            comment TEXT NOT NULL DEFAULT '',
            review TEXT NOT NULL DEFAULT '',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_ts
        ON manual_trade_journal(ts DESC);

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_symbol
        ON manual_trade_journal(symbol, ts DESC);

        CREATE INDEX IF NOT EXISTS idx_manual_trade_journal_source
        ON manual_trade_journal(source, trade_mode);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def sync_from_broker_order_snapshots(self) -> int:
        """
        Русский комментарий:
        Синхронизирует факты реальных брокерских исполнений из broker_order_snapshots.
        Важно: broker_order_snapshots сейчас не содержит цену исполнения,
        поэтому price сохраняется как 0.0, а comment фиксирует необходимость уточнения.
        """

        sql = """
        INSERT INTO manual_trade_journal (
            broker_event_id,
            ts,
            symbol,
            side,
            qty,
            entry_price,
            price,
            source,
            trade_mode,
            comment
        )
        SELECT
            'broker_order_snapshot:' || s.order_id AS broker_event_id,
            MIN(s.ts) AS ts,
            s.symbol,
            s.side,
            MAX(COALESCE(s.filled_qty, 0)) AS qty,
            0.0 AS entry_price,
            0.0 AS price,
            'BROKER_ORDER_SNAPSHOT',
            'REAL_MANUAL_BROKER',
            'Цена исполнения отсутствует в broker_order_snapshots; требуется источник брокерских сделок с ценой.'
        FROM broker_order_snapshots s
        WHERE s.symbol IS NOT NULL
          AND s.symbol <> ''
          AND s.order_id IS NOT NULL
          AND s.order_id <> ''
          AND COALESCE(s.filled_qty, 0) > 0
          AND LOWER(COALESCE(s.source, '')) NOT IN ('paper', 'replay', 'backtest', 'dry_run')
          AND LOWER(COALESCE(s.status, '')) NOT LIKE '%dry%'
          AND NOT EXISTS (
              SELECT 1
              FROM manual_trade_journal m
              WHERE m.broker_event_id = 'broker_order_snapshot:' || s.order_id
          )
        GROUP BY s.order_id, s.symbol, s.side
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                inserted = cur.rowcount
            conn.commit()

        return int(inserted)
