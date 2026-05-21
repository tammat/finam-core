from __future__ import annotations

import psycopg

from finam_core.analytics.intrabar_mae_mfe import (
    MarketBar,
    TradeWindow,
    IntrabarQuality,
    reconstruct_intrabar_quality,
)
from finam_core.analytics.statistics_repository import StatisticsRepository
from finam_core.analytics.trade_path_reconstruction import (
    TradePathInput,
    reconstruct_trade_paths,
)


class IntrabarAnalyticsRepository(StatisticsRepository):
    def migrate_intrabar_trade_quality(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_intrabar_trade_quality (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_index INTEGER NOT NULL,
            side TEXT NOT NULL,
            entry_price NUMERIC NOT NULL,
            exit_price NUMERIC NOT NULL,
            qty NUMERIC NOT NULL,
            pnl NUMERIC NOT NULL,
            mae NUMERIC NOT NULL,
            mfe NUMERIC NOT NULL,
            max_favorable_price NUMERIC NOT NULL,
            max_adverse_price NUMERIC NOT NULL,
            exit_efficiency NUMERIC NOT NULL,
            reconstruction_mode TEXT NOT NULL DEFAULT 'real_market_bars',
            path_confidence NUMERIC NOT NULL DEFAULT 1.0,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_intrabar_quality_symbol
        ON analytics_intrabar_trade_quality(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_intrabar_quality_strategy
        ON analytics_intrabar_trade_quality(strategy);

        ALTER TABLE analytics_intrabar_trade_quality
        ADD COLUMN IF NOT EXISTS reconstruction_mode TEXT NOT NULL DEFAULT 'real_market_bars';

        ALTER TABLE analytics_intrabar_trade_quality
        ADD COLUMN IF NOT EXISTS path_confidence NUMERIC NOT NULL DEFAULT 1.0;
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def _columns(self, table_name: str) -> set[str]:
        sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (table_name,))
                return {str(row[0]) for row in cur.fetchall()}

    def load_trade_windows(self, symbol: str) -> list[TradeWindow]:
        columns = self._columns("trades")

        time_expr = (
            "created_at"
            if "created_at" in columns
            else "ts"
            if "ts" in columns
            else "executed_at"
            if "executed_at" in columns
            else "now()"
        )

        side_expr = (
            "side"
            if "side" in columns
            else "direction"
            if "direction" in columns
            else "'unknown'"
        )

        price_expr = (
            "price"
            if "price" in columns
            else "fill_price"
            if "fill_price" in columns
            else "0"
        )

        qty_expr = (
            "qty"
            if "qty" in columns
            else "quantity"
            if "quantity" in columns
            else "0"
        )

        order_expr = "id" if "id" in columns else time_expr

        sql = f"""
        SELECT
            symbol,
            {side_expr} AS side,
            CASE
                WHEN payload ? 'trade_id'
                 AND split_part(payload->>'trade_id', '_', array_length(string_to_array(payload->>'trade_id', '_'), 1)) ~ '^[0-9]+$'
                THEN to_timestamp(
                    split_part(
                        payload->>'trade_id',
                        '_',
                        array_length(string_to_array(payload->>'trade_id', '_'), 1)
                    )::double precision / 1000.0
                )
                ELSE {time_expr}
            END AS trade_time,
            COALESCE({price_expr}, 0) AS price,
            COALESCE({qty_expr}, 0) AS qty
        FROM trades
        WHERE symbol = %s
        ORDER BY {order_expr} ASC
        """

        windows: list[TradeWindow] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol,))
                fills = cur.fetchall()

        open_trade = None
        trade_index = 0

        for row in fills:
            row_symbol = str(row[0])
            side = str(row[1]).lower()
            trade_time = row[2]
            price = float(row[3])
            qty = float(row[4])

            if qty <= 0 or price <= 0:
                continue

            if side in {"buy", "b", "long"} and open_trade is None:
                open_trade = {
                    "entry_time": trade_time,
                    "entry_price": price,
                    "qty": qty,
                }
                continue

            if side in {"sell", "s", "short"} and open_trade is not None:
                trade_index += 1
                pnl = (price - open_trade["entry_price"]) * min(qty, open_trade["qty"])

                windows.append(
                    TradeWindow(
                        trade_index=trade_index,
                        symbol=row_symbol,
                        side="long",
                        entry_time=open_trade["entry_time"],
                        exit_time=trade_time,
                        entry_price=open_trade["entry_price"],
                        exit_price=price,
                        qty=min(qty, open_trade["qty"]),
                        pnl=round(pnl, 10),
                    )
                )

                open_trade = None

        return windows

    def load_market_bars_for_symbol(self, symbol: str, timeframe: str) -> list[MarketBar]:
        columns = self._columns("market_bars")

        ts_expr = (
            "ts"
            if "ts" in columns
            else "timestamp"
            if "timestamp" in columns
            else "bar_time"
            if "bar_time" in columns
            else "created_at"
        )

        timeframe_filter = ""
        params: list[object] = [symbol]

        if "timeframe" in columns:
            timeframe_filter = "AND timeframe = %s"
            params.append(timeframe)

        sql = f"""
        SELECT
            symbol,
            {ts_expr} AS ts,
            high,
            low,
            close
        FROM market_bars
        WHERE symbol = %s
        {timeframe_filter}
        ORDER BY {ts_expr} ASC
        """

        bars: list[MarketBar] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, params)
                for row in cur.fetchall():
                    bars.append(
                        MarketBar(
                            symbol=str(row[0]),
                            ts=row[1],
                            high=float(row[2]),
                            low=float(row[3]),
                            close=float(row[4]),
                        )
                    )

        return bars

    def build_intrabar_quality(
        self,
        symbol: str,
        timeframe: str,
    ) -> list[IntrabarQuality]:
        trades = self.load_trade_windows(symbol=symbol)
        bars = self.load_market_bars_for_symbol(symbol=symbol, timeframe=timeframe)

        if bars:
            return reconstruct_intrabar_quality(
                trades=trades,
                bars=bars,
            )

        reconstructed = reconstruct_trade_paths(
            [
                TradePathInput(
                    trade_index=t.trade_index,
                    symbol=t.symbol,
                    side=t.side,
                    entry_price=t.entry_price,
                    exit_price=t.exit_price,
                    qty=t.qty,
                    pnl=t.pnl,
                )
                for t in trades
            ]
        )

        return [
            IntrabarQuality(
                trade_index=item.trade_index,
                symbol=item.symbol,
                side=item.side,
                entry_price=item.entry_price,
                exit_price=item.exit_price,
                qty=item.qty,
                pnl=item.pnl,
                mae=item.reconstructed_mae,
                mfe=item.reconstructed_mfe,
                max_favorable_price=item.reconstructed_high,
                max_adverse_price=item.reconstructed_low,
                exit_efficiency=item.exit_efficiency,
            )
            for item in reconstructed
        ]

    def save_intrabar_quality(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        qualities: list[IntrabarQuality],
    ) -> None:
        sql = """
        INSERT INTO analytics_intrabar_trade_quality (
            symbol,
            strategy,
            timeframe,
            trade_index,
            side,
            entry_price,
            exit_price,
            qty,
            pnl,
            mae,
            mfe,
            max_favorable_price,
            max_adverse_price,
            exit_efficiency,
            reconstruction_mode,
            path_confidence
        )
        VALUES (
            %s, %s, %s,
            %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                for item in qualities:
                    cur.execute(
                        sql,
                        (
                            symbol,
                            strategy,
                            timeframe,
                            item.trade_index,
                            item.side,
                            item.entry_price,
                            item.exit_price,
                            item.qty,
                            item.pnl,
                            item.mae,
                            item.mfe,
                            item.max_favorable_price,
                            item.max_adverse_price,
                            item.exit_efficiency,
                            "fallback_trade_path",
                            0.35,
                        ),
                    )
            conn.commit()
