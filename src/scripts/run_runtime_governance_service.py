from __future__ import annotations

import argparse
import signal
import time
from datetime import datetime, timezone

from finam_core.analytics.strategy_rank_persistence import StrategyRankPersistence
from finam_core.analytics.strategy_scorecard_persistence import StrategyScorecardPersistence
from finam_core.runtime.runtime_governance_coordinator import RuntimeGovernanceCoordinator
from finam_core.runtime.runtime_governance_telemetry import RuntimeGovernanceTelemetry
from finam_core.runtime.runtime_strategy_cooldown_builder import RuntimeStrategyCooldownBuilder
from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator
from finam_core.storage.postgres_logger import PostgresLogger


shutdown_requested = False


def request_shutdown(signum=None, frame=None) -> None:
    global shutdown_requested
    shutdown_requested = True
    print(f"RUNTIME_GOVERNANCE_SERVICE_SHUTDOWN_REQUESTED signal={signum}", flush=True)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument("--interval-sec", type=int, default=3600)
    parser.add_argument("--max-symbols", type=int, default=5)
    parser.add_argument("--min-score", type=float, default=0.35)

    return parser.parse_args()


def build_coordinator() -> RuntimeGovernanceCoordinator:
    pg_logger = PostgresLogger()

    return RuntimeGovernanceCoordinator(
        scorecard_persistence=StrategyScorecardPersistence(pg_logger),
        rank_persistence=StrategyRankPersistence(pg_logger),
        cooldown_builder=RuntimeStrategyCooldownBuilder(pg_logger),
        allocator=RuntimeUniverseAllocator(pg_logger),
        telemetry=RuntimeGovernanceTelemetry(pg_logger),
    )


def main() -> int:
    args = parse_args()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    coordinator = build_coordinator()

    print(
        "RUNTIME_GOVERNANCE_SERVICE_START "
        f"interval_sec={args.interval_sec} "
        f"max_symbols={args.max_symbols} "
        f"min_score={args.min_score}",
        flush=True,
    )

    while not shutdown_requested:
        trade_date = datetime.now(timezone.utc).date()

        try:
            coordinator.run_daily(
                trade_date=trade_date,
                max_symbols=args.max_symbols,
                min_score=args.min_score,
            )
        except Exception as exc:
            print(
                f"RUNTIME_GOVERNANCE_SERVICE_ERROR type={type(exc).__name__} error={exc}",
                flush=True,
            )

        sleep_left = args.interval_sec

        while sleep_left > 0 and not shutdown_requested:
            step = min(5, sleep_left)
            time.sleep(step)
            sleep_left -= step

    print("RUNTIME_GOVERNANCE_SERVICE_STOPPED", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
