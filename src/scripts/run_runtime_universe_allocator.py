from __future__ import annotations

import os

from finam_core.runtime.runtime_universe_allocator import RuntimeUniverseAllocator
from finam_core.storage.postgres_logger import PostgresLogger


def main() -> int:
    max_symbols = int(os.getenv("RUNTIME_ACTIVE_UNIVERSE_LIMIT", "5"))
    min_score = float(os.getenv("RUNTIME_ACTIVE_UNIVERSE_MIN_SCORE", "0.35"))

    allocator = RuntimeUniverseAllocator(PostgresLogger())
    active_count = allocator.allocate(max_symbols=max_symbols, min_score=min_score)

    print(
        f"OK: runtime active universe allocated "
        f"active={active_count} max_symbols={max_symbols} min_score={min_score}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
