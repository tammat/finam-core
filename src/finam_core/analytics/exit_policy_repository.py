from __future__ import annotations

import psycopg

from finam_core.analytics.exit_policy_simulator import (
    ExitPolicyCandidate,
    ExitPolicyInput,
    ExitPolicySimulationResult,
    simulate_exit_policies,
)
from finam_core.analytics.statistics_repository import StatisticsRepository


class ExitPolicySimulationRepository(StatisticsRepository):
    def migrate_exit_policy_simulation(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_exit_policy_simulation (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            policy_name TEXT NOT NULL,
            take_distance NUMERIC NOT NULL,
            stop_distance NUMERIC NOT NULL,
            simulated_trades INTEGER NOT NULL,
            simulated_wins INTEGER NOT NULL,
            simulated_losses INTEGER NOT NULL,
            simulated_winrate NUMERIC NOT NULL,
            simulated_net_pnl NUMERIC NOT NULL,
            simulated_profit_factor NUMERIC NOT NULL,
            simulated_max_drawdown NUMERIC NOT NULL,
            simulated_avg_pnl NUMERIC NOT NULL,
            simulated_sharpe_like NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_policy_simulation_symbol
        ON analytics_exit_policy_simulation(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_policy_simulation_strategy
        ON analytics_exit_policy_simulation(strategy);

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_policy_simulation_calculated_at
        ON analytics_exit_policy_simulation(calculated_at);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def load_exit_policy_samples(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> list[ExitPolicyInput]:
        sql = """
        SELECT
            pnl,
            mae,
            mfe
        FROM analytics_intrabar_trade_quality
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
        ORDER BY trade_index ASC
        """

        result: list[ExitPolicyInput] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, strategy, timeframe))

                for row in cur.fetchall():
                    result.append(
                        ExitPolicyInput(
                            pnl=float(row[0]),
                            mae=float(row[1]),
                            mfe=float(row[2]),
                        )
                    )

        return result

    def load_latest_exit_optimization_candidates(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> list[ExitPolicyCandidate]:
        sql = """
        SELECT
            recommended_take_50,
            recommended_take_70,
            recommended_take_80,
            recommended_stop_50,
            recommended_stop_70,
            recommended_stop_80
        FROM analytics_exit_optimization
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
        ORDER BY calculated_at DESC
        LIMIT 1
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, strategy, timeframe))
                row = cur.fetchone()

        if not row:
            return []

        take50 = float(row[0])
        take70 = float(row[1])
        take80 = float(row[2])
        stop50 = float(row[3])
        stop70 = float(row[4])
        stop80 = float(row[5])

        return [
            ExitPolicyCandidate("take50_stop50", take50, stop50),
            ExitPolicyCandidate("take70_stop50", take70, stop50),
            ExitPolicyCandidate("take70_stop70", take70, stop70),
            ExitPolicyCandidate("take80_stop50", take80, stop50),
            ExitPolicyCandidate("take80_stop70", take80, stop70),
            ExitPolicyCandidate("take80_stop80", take80, stop80),
        ]

    def build_simulation(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> list[ExitPolicySimulationResult]:
        samples = self.load_exit_policy_samples(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        candidates = self.load_latest_exit_optimization_candidates(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        return simulate_exit_policies(
            samples=samples,
            candidates=candidates,
        )

    def save_simulation_results(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        results: list[ExitPolicySimulationResult],
    ) -> None:
        sql = """
        INSERT INTO analytics_exit_policy_simulation (
            symbol,
            strategy,
            timeframe,
            policy_name,
            take_distance,
            stop_distance,
            simulated_trades,
            simulated_wins,
            simulated_losses,
            simulated_winrate,
            simulated_net_pnl,
            simulated_profit_factor,
            simulated_max_drawdown,
            simulated_avg_pnl,
            simulated_sharpe_like
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
                for item in results:
                    cur.execute(
                        sql,
                        (
                            symbol,
                            strategy,
                            timeframe,
                            item.policy_name,
                            item.take_distance,
                            item.stop_distance,
                            item.simulated_trades,
                            item.simulated_wins,
                            item.simulated_losses,
                            item.simulated_winrate,
                            item.simulated_net_pnl,
                            item.simulated_profit_factor,
                            item.simulated_max_drawdown,
                            item.simulated_avg_pnl,
                            item.simulated_sharpe_like,
                        ),
                    )
            conn.commit()
