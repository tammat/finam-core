from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import StatisticsRepository


class ExitPolicySelector(StatisticsRepository):
    def migrate_selected_policy(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_exit_policy_selected (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            selected_policy TEXT NOT NULL,
            take_distance NUMERIC NOT NULL,
            stop_distance NUMERIC NOT NULL,
            profit_factor NUMERIC NOT NULL,
            net_pnl NUMERIC NOT NULL,
            max_drawdown NUMERIC NOT NULL,
            winrate NUMERIC NOT NULL,
            reason TEXT NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            selected_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_exit_policy_selected_active
        ON analytics_exit_policy_selected(symbol, strategy, timeframe, is_active);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def select_best_policy(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        min_profit_factor: float = 1.2,
        max_allowed_drawdown: float = -999999.0,
    ) -> dict | None:
        sql = """
        SELECT
            policy_name,
            take_distance,
            stop_distance,
            simulated_profit_factor,
            simulated_net_pnl,
            simulated_max_drawdown,
            simulated_winrate
        FROM analytics_exit_policy_simulation
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
          AND simulated_profit_factor >= %s
          AND simulated_max_drawdown >= %s
        ORDER BY
            simulated_profit_factor DESC,
            simulated_net_pnl DESC,
            simulated_max_drawdown DESC
        LIMIT 1
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    sql,
                    (
                        symbol,
                        strategy,
                        timeframe,
                        min_profit_factor,
                        max_allowed_drawdown,
                    ),
                )
                row = cur.fetchone()

        if not row:
            return None

        return {
            "selected_policy": str(row[0]),
            "take_distance": float(row[1]),
            "stop_distance": float(row[2]),
            "profit_factor": float(row[3]),
            "net_pnl": float(row[4]),
            "max_drawdown": float(row[5]),
            "winrate": float(row[6]),
            "reason": (
                "selected_by_profit_factor_then_net_pnl_then_drawdown; "
                f"min_profit_factor={min_profit_factor}; "
                f"max_allowed_drawdown={max_allowed_drawdown}"
            ),
        }

    def save_selected_policy(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        selected: dict,
    ) -> None:
        deactivate_sql = """
        UPDATE analytics_exit_policy_selected
        SET is_active = FALSE
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
          AND is_active = TRUE
        """

        insert_sql = """
        INSERT INTO analytics_exit_policy_selected (
            symbol,
            strategy,
            timeframe,
            selected_policy,
            take_distance,
            stop_distance,
            profit_factor,
            net_pnl,
            max_drawdown,
            winrate,
            reason,
            is_active
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s,
            TRUE
        )
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(deactivate_sql, (symbol, strategy, timeframe))
                cur.execute(
                    insert_sql,
                    (
                        symbol,
                        strategy,
                        timeframe,
                        selected["selected_policy"],
                        selected["take_distance"],
                        selected["stop_distance"],
                        selected["profit_factor"],
                        selected["net_pnl"],
                        selected["max_drawdown"],
                        selected["winrate"],
                        selected["reason"],
                    ),
                )
            conn.commit()
