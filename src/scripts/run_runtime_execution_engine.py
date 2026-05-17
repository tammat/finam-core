from __future__ import annotations

import os

from finam_core.data.runtime_universe_provider import RuntimeUniverseProvider
from finam_core.runtime.runtime_execution_engine import RuntimeExecutionEngine
from finam_core.runtime.runtime_rebalance_cycle import RuntimeRebalanceCycle
from finam_core.runtime.runtime_telemetry import RuntimeTelemetry
from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator
from finam_core.storage.postgres_logger import PostgresLogger


def main() -> None:
    pg_logger = PostgresLogger()

    provider = RuntimeUniverseProvider(pg_logger)
    allocator = RuntimeUniverseAllocator(pg_logger)

    rebalance_cycle = RuntimeRebalanceCycle(
        allocator,
        max_symbols=int(os.getenv("RUNTIME_MAX_SYMBOLS", "5")),
        min_score=float(os.getenv("RUNTIME_MIN_SCORE", "0.35")),
    )

    telemetry = RuntimeTelemetry(pg_logger)

    engine = RuntimeExecutionEngine(
        universe_provider=provider,
        telemetry=telemetry,
        supervisor_interval_sec=float(os.getenv("RUNTIME_SUPERVISOR_INTERVAL_SEC", "5")),
        rebalance_interval_sec=float(os.getenv("RUNTIME_REBALANCE_INTERVAL_SEC", "60")),
        rebalance_callback=rebalance_cycle,
    )

    print("RUNTIME_EXECUTION_ENGINE_V3_START", flush=True)
    engine.run_forever()


if __name__ == "__main__":
    main()
