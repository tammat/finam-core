from __future__ import annotations

import os
import psycopg

from finam_core.analytics.pnl_reconstruction import (
    TradeFill,
    reconstruct_closed_trades_fifo,
)
from finam_core.analytics.trade_statistics import (
    ClosedTrade,
    TradeStatistics,
)


def build_psycopg_url() -> str:
    database_url = os.getenv("DATABASE_URL")

    if database_url:
        return (
            database_url
            .replace("postgresql+psycopg2://", "postgresql://")
            .replace("postgresql+psycopg://", "postgresql://")
        )

    return (
        f"postgresql://{os.getenv('DB_USER', 'finam')}:"
        f"{os.getenv('DB_PASSWORD', '')}@"
        f"{os.getenv('DB_HOST', 'localhost')}:"
        f"{os.getenv('DB_PORT', '5432')}/"
        f"{os.getenv('DB_NAME', 'finam_core')}"
    )


class StatisticsRepository:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = database_url or build_psycopg_url()

    def migrate(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_trade_statistics (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            strategy TEXT NOT NULL,
            trades INTEGER NOT NULL,
            wins INTEGER NOT NULL,
            losses INTEGER NOT NULL,
            winrate NUMERIC NOT NULL,
            gross_profit NUMERIC NOT NULL,
            gross_loss NUMERIC NOT NULL,
            net_pnl NUMERIC NOT NULL,
            avg_pnl NUMERIC NOT NULL,
            profit_factor NUMERIC NOT NULL,
            max_drawdown NUMERIC NOT NULL,
            expectancy NUMERIC NOT NULL,
            sharpe_like NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_trade_statistics_symbol
        ON analytics_trade_statistics(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_trade_statistics_strategy
        ON analytics_trade_statistics(strategy);

        CREATE INDEX IF NOT EXISTS idx_analytics_trade_statistics_calculated_at
        ON analytics_trade_statistics(calculated_at);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def _trade_columns(self) -> set[str]:
        sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'trades'
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return {str(row[0]) for row in cur.fetchall()}

    def load_fills(self, symbol: str) -> list[TradeFill]:
        """
        Загружает фактические исполнения из trades.

        Поддерживаем разные варианты схемы:
        - side / direction
        - price / fill_price
        - qty / quantity
        """

        columns = self._trade_columns()

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

        order_expr = (
            "id"
            if "id" in columns
            else "created_at"
            if "created_at" in columns
            else "symbol"
        )

        commission_candidates = [
            name for name in (
                "commission",
                "broker_commission",
                "exchange_commission",
                "total_commission",
                "fee",
            )
            if name in columns
        ]

        if commission_candidates:
            commission_expr = "COALESCE(" + ", ".join(commission_candidates + ["0"]) + ")"
        else:
            commission_expr = "0"

        sql = f"""
        SELECT
            symbol,
            {side_expr} AS side,
            COALESCE({price_expr}, 0) AS price,
            COALESCE({qty_expr}, 0) AS qty,
            {commission_expr} AS commission
        FROM trades
        WHERE symbol = %s
        ORDER BY {order_expr} ASC
        """

        result: list[TradeFill] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol,))
                for row in cur.fetchall():
                    result.append(
                        TradeFill(
                            symbol=str(row[0]),
                            side=str(row[1]),
                            price=float(row[2]),
                            qty=float(row[3]),
                            commission=float(row[4]),
                        )
                    )

        return result

    def load_closed_trades(
        self,
        symbol: str,
        fallback_commission_rate: float = 0.0,
    ) -> list[ClosedTrade]:
        fills = self.load_fills(symbol=symbol)
        reconstructed = reconstruct_closed_trades_fifo(
            symbol=symbol,
            fills=fills,
            fallback_commission_rate=fallback_commission_rate,
        )

        return [
            ClosedTrade(
                symbol=item.symbol,
                side=item.side,
                entry_price=item.entry_price,
                exit_price=item.exit_price,
                qty=item.qty,
                pnl=item.pnl,
            )
            for item in reconstructed
        ]



    def migrate_equity_curve(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_equity_curve (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_index INTEGER NOT NULL,
            pnl NUMERIC NOT NULL,
            cumulative_pnl NUMERIC NOT NULL,
            peak_equity NUMERIC NOT NULL,
            drawdown NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_equity_curve_symbol
        ON analytics_equity_curve(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_equity_curve_strategy
        ON analytics_equity_curve(strategy);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save_equity_curve(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        points,
    ) -> None:

        sql = """
        INSERT INTO analytics_equity_curve (
            symbol,
            strategy,
            timeframe,
            trade_index,
            pnl,
            cumulative_pnl,
            peak_equity,
            drawdown
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:

                for point in points:
                    cur.execute(
                        sql,
                        (
                            symbol,
                            strategy,
                            timeframe,
                            point.trade_index,
                            point.pnl,
                            point.cumulative_pnl,
                            point.peak_equity,
                            point.drawdown,
                        ),
                    )

            conn.commit()



    def migrate_drawdown_summary(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_drawdown_summary (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trades INTEGER NOT NULL,
            final_pnl NUMERIC NOT NULL,
            max_drawdown NUMERIC NOT NULL,
            max_drawdown_trade_index INTEGER NOT NULL,
            max_win_streak INTEGER NOT NULL,
            max_loss_streak INTEGER NOT NULL,
            avg_win NUMERIC NOT NULL,
            avg_loss NUMERIC NOT NULL,
            payoff_ratio NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_drawdown_summary_symbol
        ON analytics_drawdown_summary(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_drawdown_summary_strategy
        ON analytics_drawdown_summary(strategy);

        CREATE INDEX IF NOT EXISTS idx_analytics_drawdown_summary_calculated_at
        ON analytics_drawdown_summary(calculated_at);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()



    def migrate_trade_quality(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_trade_quality (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trade_index INTEGER NOT NULL,
            pnl NUMERIC NOT NULL,
            mfe NUMERIC NOT NULL,
            mae NUMERIC NOT NULL,
            efficiency NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_trade_quality_symbol
        ON analytics_trade_quality(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_trade_quality_strategy
        ON analytics_trade_quality(strategy);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def save_trade_quality(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        qualities,
    ) -> None:

        sql = """
        INSERT INTO analytics_trade_quality (
            symbol,
            strategy,
            timeframe,
            trade_index,
            pnl,
            mfe,
            mae,
            efficiency
        )
        VALUES (
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
                            item.pnl,
                            item.mfe,
                            item.mae,
                            item.efficiency,
                        ),
                    )

            conn.commit()

    def save_drawdown_summary(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        summary,
    ) -> None:
        sql = """
        INSERT INTO analytics_drawdown_summary (
            symbol,
            strategy,
            timeframe,
            trades,
            final_pnl,
            max_drawdown,
            max_drawdown_trade_index,
            max_win_streak,
            max_loss_streak,
            avg_win,
            avg_loss,
            payoff_ratio
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        symbol,
                        strategy,
                        timeframe,
                        summary.trades,
                        summary.final_pnl,
                        summary.max_drawdown,
                        summary.max_drawdown_trade_index,
                        summary.max_win_streak,
                        summary.max_loss_streak,
                        summary.avg_win,
                        summary.avg_loss,
                        summary.payoff_ratio,
                    ),
                )
            conn.commit()

    def save_statistics(
        self,
        stats: TradeStatistics,
        timeframe: str,
        strategy: str,
    ) -> None:
        sql = """
        INSERT INTO analytics_trade_statistics (
            symbol, timeframe, strategy,
            trades, wins, losses,
            winrate, gross_profit, gross_loss,
            net_pnl, avg_pnl, profit_factor,
            max_drawdown, expectancy, sharpe_like
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        stats.symbol,
                        timeframe,
                        strategy,
                        stats.trades,
                        stats.wins,
                        stats.losses,
                        stats.winrate,
                        stats.gross_profit,
                        stats.gross_loss,
                        stats.net_pnl,
                        stats.avg_pnl,
                        stats.profit_factor,
                        stats.max_drawdown,
                        stats.expectancy,
                        stats.sharpe_like,
                    ),
                )
            conn.commit()
