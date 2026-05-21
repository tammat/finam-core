from __future__ import annotations

import psycopg

from finam_core.analytics.exit_optimization import (
    IntrabarTradeSample,
    ExitOptimizationProfile,
    build_exit_optimization_profile,
)
from finam_core.analytics.statistics_repository import StatisticsRepository


class ExitOptimizationRepository(StatisticsRepository):
    def migrate_exit_optimization(self) -> None:
        sql = """
        CREATE TABLE IF NOT EXISTS analytics_exit_optimization (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            strategy TEXT NOT NULL,
            timeframe TEXT NOT NULL,
            trades INTEGER NOT NULL,
            avg_pnl NUMERIC NOT NULL,
            avg_mfe NUMERIC NOT NULL,
            avg_mae NUMERIC NOT NULL,
            avg_exit_efficiency NUMERIC NOT NULL,
            p50_mfe NUMERIC NOT NULL,
            p70_mfe NUMERIC NOT NULL,
            p80_mfe NUMERIC NOT NULL,
            p50_mae_abs NUMERIC NOT NULL,
            p70_mae_abs NUMERIC NOT NULL,
            p80_mae_abs NUMERIC NOT NULL,
            recommended_take_50 NUMERIC NOT NULL,
            recommended_take_70 NUMERIC NOT NULL,
            recommended_take_80 NUMERIC NOT NULL,
            recommended_stop_50 NUMERIC NOT NULL,
            recommended_stop_70 NUMERIC NOT NULL,
            recommended_stop_80 NUMERIC NOT NULL,
            calculated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_optimization_symbol
        ON analytics_exit_optimization(symbol);

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_optimization_strategy
        ON analytics_exit_optimization(strategy);

        CREATE INDEX IF NOT EXISTS idx_analytics_exit_optimization_calculated_at
        ON analytics_exit_optimization(calculated_at);
        """

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
            conn.commit()

    def load_intrabar_samples(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> list[IntrabarTradeSample]:
        sql = """
        SELECT
            pnl,
            mae,
            mfe,
            exit_efficiency
        FROM analytics_intrabar_trade_quality
        WHERE symbol = %s
          AND strategy = %s
          AND timeframe = %s
        ORDER BY trade_index ASC
        """

        result: list[IntrabarTradeSample] = []

        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (symbol, strategy, timeframe))

                for row in cur.fetchall():
                    result.append(
                        IntrabarTradeSample(
                            pnl=float(row[0]),
                            mae=float(row[1]),
                            mfe=float(row[2]),
                            exit_efficiency=float(row[3]),
                        )
                    )

        return result

    def build_profile(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
    ) -> ExitOptimizationProfile:
        samples = self.load_intrabar_samples(
            symbol=symbol,
            strategy=strategy,
            timeframe=timeframe,
        )

        return build_exit_optimization_profile(samples)

    def save_profile(
        self,
        symbol: str,
        strategy: str,
        timeframe: str,
        profile: ExitOptimizationProfile,
    ) -> None:
        sql = """
        INSERT INTO analytics_exit_optimization (
            symbol,
            strategy,
            timeframe,
            trades,
            avg_pnl,
            avg_mfe,
            avg_mae,
            avg_exit_efficiency,
            p50_mfe,
            p70_mfe,
            p80_mfe,
            p50_mae_abs,
            p70_mae_abs,
            p80_mae_abs,
            recommended_take_50,
            recommended_take_70,
            recommended_take_80,
            recommended_stop_50,
            recommended_stop_70,
            recommended_stop_80
        )
        VALUES (
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s, %s,
            %s, %s
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
                        profile.trades,
                        profile.avg_pnl,
                        profile.avg_mfe,
                        profile.avg_mae,
                        profile.avg_exit_efficiency,
                        profile.p50_mfe,
                        profile.p70_mfe,
                        profile.p80_mfe,
                        profile.p50_mae_abs,
                        profile.p70_mae_abs,
                        profile.p80_mae_abs,
                        profile.recommended_take_50,
                        profile.recommended_take_70,
                        profile.recommended_take_80,
                        profile.recommended_stop_50,
                        profile.recommended_stop_70,
                        profile.recommended_stop_80,
                    ),
                )
            conn.commit()
