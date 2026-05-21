from __future__ import annotations

import psycopg

from finam_core.analytics.symbol_strategy_resolver import SymbolStrategyResolver
from finam_core.portfolio.portfolio_intelligence_snapshot import (
    PortfolioIntelligenceSnapshot,
    build_portfolio_intelligence_snapshot,
)


class PortfolioIntelligenceRepository:
    """
    Русский комментарий:
    Read-only repository для Portfolio Intelligence Layer.
    """

    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.strategy_resolver = SymbolStrategyResolver(database_url)

    def load_positions(self) -> list[dict]:
        for table in (
            "real_position_snapshots",
            "managed_positions",
            "position_lifecycle_state",
            "positions",
        ):
            rows = self._try_load_positions_from_table(table)
            if rows:
                return rows

        return []

    def _try_load_positions_from_table(self, table: str) -> list[dict]:
        columns = self._columns(table)

        if "symbol" not in columns:
            return []

        if table == "real_position_snapshots":
            return self._load_latest_real_position_snapshots(columns)

        qty_col = self._first_existing(columns, ["qty", "quantity", "position_qty", "remaining_qty"])
        avg_col = self._first_existing(columns, ["avg_price", "average_price", "entry_price"])
        current_col = self._first_existing(columns, ["current_price", "market_price", "last_price", "price", "entry_price"])

        if not qty_col:
            return []

        avg_expr = avg_col if avg_col else "0"
        current_expr = current_col if current_col else avg_expr

        sql = f"""
        SELECT
            symbol,
            COALESCE({qty_col}, 0) AS qty,
            COALESCE({avg_expr}, 0) AS avg_price,
            COALESCE({current_expr}, 0) AS current_price
        FROM {table}
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    result = []
                    for row in cur.fetchall():
                        result.append(
                            {
                                "symbol": str(row[0]),
                                "qty": float(row[1] or 0.0),
                                "avg_price": float(row[2] or 0.0),
                                "current_price": float(row[3] or 0.0),
                            }
                        )
                    return result
        except Exception:
            return []


    def _load_latest_real_position_snapshots(self, columns: set[str]) -> list[dict]:
        qty_col = self._first_existing(columns, ["qty", "quantity", "position_qty"])
        avg_col = self._first_existing(columns, ["avg_price", "average_price"])
        current_col = self._first_existing(columns, ["market_price", "current_price", "last_price", "price"])

        if not qty_col:
            return []

        avg_expr = avg_col if avg_col else "0"
        current_expr = current_col if current_col else avg_expr

        raw_price_expr = "0"
        if "raw_json" in columns:
            raw_price_expr = """
            COALESCE(
                NULLIF(raw_json->'current_price'->>'value', '')::numeric,
                NULLIF(raw_json->'market_price'->>'value', '')::numeric,
                NULLIF(raw_json->>'current_price', '')::numeric,
                NULLIF(raw_json->>'market_price', '')::numeric,
                NULLIF(raw_json->'raw'->>'current_price', '')::numeric,
                NULLIF(raw_json->'raw'->>'market_price', '')::numeric,
                0
            )
            """

        sql = f"""
        SELECT DISTINCT ON (symbol)
            symbol,
            COALESCE({qty_col}, 0) AS qty,
            COALESCE({avg_expr}, 0) AS avg_price,
            CASE
                WHEN COALESCE({current_expr}, 0) > 0
                THEN COALESCE({current_expr}, 0)
                ELSE {raw_price_expr}
            END AS current_price
        FROM real_position_snapshots
        WHERE symbol IS NOT NULL
          AND symbol <> ''
        ORDER BY symbol, ts DESC, id DESC
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    return [
                        {
                            "symbol": str(row[0]),
                            "qty": float(row[1] or 0.0),
                            "avg_price": float(row[2] or 0.0),
                            "current_price": float(row[3] or 0.0),
                        }
                        for row in cur.fetchall()
                    ]
        except Exception:
            return []


    def load_strategy_by_symbol(self, symbols: list[str]) -> dict[str, str]:
        return {
            symbol: self.strategy_resolver.resolve(symbol)
            for symbol in symbols
        }

    def load_realized_pnl_by_symbol(self) -> dict[str, float]:
        result: dict[str, float] = {}

        for table in ("analytics_trade_statistics", "trades"):
            if table == "analytics_trade_statistics":
                rows = self._try_load_realized_from_statistics()
            else:
                rows = self._try_load_realized_from_trades()

            if rows:
                result.update(rows)
                break

        return result

    def _try_load_realized_from_statistics(self) -> dict[str, float]:
        columns = self._columns("analytics_trade_statistics")
        if not {"symbol", "net_pnl"}.issubset(columns):
            return {}

        sql = """
        SELECT DISTINCT ON (symbol)
            symbol,
            net_pnl
        FROM analytics_trade_statistics
        ORDER BY symbol, calculated_at DESC
        """

        return self._load_symbol_float_map(sql)

    def _try_load_realized_from_trades(self) -> dict[str, float]:
        columns = self._columns("trades")
        if "symbol" not in columns:
            return {}

        pnl_col = self._first_existing(columns, ["pnl", "realized_pnl"])
        if not pnl_col:
            return {}

        sql = f"""
        SELECT symbol, SUM(COALESCE({pnl_col}, 0))
        FROM trades
        GROUP BY symbol
        """

        return self._load_symbol_float_map(sql)

    def load_strategy_health_by_symbol(self) -> dict[str, str]:
        columns = self._columns("strategy_performance_history")

        if not {"symbol", "status"}.issubset(columns):
            return {}

        sql = """
        SELECT DISTINCT ON (symbol)
            symbol,
            status
        FROM strategy_performance_history
        ORDER BY symbol, created_at DESC
        """

        result: dict[str, str] = {}

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    for row in cur.fetchall():
                        result[str(row[0])] = str(row[1])
        except Exception:
            return {}

        return result

    def build_snapshot(self, cash: float = 0.0) -> PortfolioIntelligenceSnapshot:
        positions = self.load_positions()
        symbols = [str(p["symbol"]) for p in positions]

        return build_portfolio_intelligence_snapshot(
            positions=positions,
            strategy_by_symbol=self.load_strategy_by_symbol(symbols),
            regime_by_symbol={},
            realized_pnl_by_symbol=self.load_realized_pnl_by_symbol(),
            strategy_health_by_symbol=self.load_strategy_health_by_symbol(),
            cash=cash,
        )

    def _load_symbol_float_map(self, sql: str) -> dict[str, float]:
        result: dict[str, float] = {}

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql)
                    for row in cur.fetchall():
                        result[str(row[0])] = float(row[1] or 0.0)
        except Exception:
            return {}

        return result

    def _columns(self, table: str) -> set[str]:
        sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = %s
        """

        try:
            with psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(sql, (table,))
                    return {str(row[0]) for row in cur.fetchall()}
        except Exception:
            return set()

    @staticmethod
    def _first_existing(columns: set[str], names: list[str]) -> str | None:
        for name in names:
            if name in columns:
                return name
        return None
