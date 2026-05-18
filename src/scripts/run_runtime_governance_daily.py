from __future__ import annotations

import argparse
from datetime import datetime

from finam_core.analytics.strategy_rank_persistence import StrategyRankPersistence
from finam_core.analytics.strategy_scorecard_persistence import StrategyScorecardPersistence
from finam_core.runtime.runtime_governance_coordinator import RuntimeGovernanceCoordinator
from finam_core.runtime.runtime_governance_telemetry import RuntimeGovernanceTelemetry
from finam_core.runtime.runtime_strategy_cooldown_builder import RuntimeStrategyCooldownBuilder
from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--date", required=True, help="Дата governance-cycle YYYY-MM-DD")
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.35)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    pg_logger = PostgresLogger()

    coordinator = RuntimeGovernanceCoordinator(
        scorecard_persistence=StrategyScorecardPersistence(pg_logger),
        rank_persistence=StrategyRankPersistence(pg_logger),
        cooldown_builder=RuntimeStrategyCooldownBuilder(pg_logger),
        allocator=RuntimeUniverseAllocator(pg_logger),
        telemetry=RuntimeGovernanceTelemetry(pg_logger),
    )

    coordinator.run_daily(
        trade_date=trade_date,
        max_symbols=args.max_symbols,
        min_score=args.min_score,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
