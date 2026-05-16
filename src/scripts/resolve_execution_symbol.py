from __future__ import annotations

import argparse

from finam_core.execution.execution_symbol_resolver import ExecutionSymbolResolver
from finam_core.storage.postgres_logger import PostgresLogger


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    args = parser.parse_args()

    decision = ExecutionSymbolResolver(PostgresLogger()).resolve(args.symbol)

    print(
        "OK: execution symbol resolved "
        f"requested={decision.requested_symbol} "
        f"execution={decision.execution_symbol} "
        f"continuous={decision.continuous_symbol} "
        f"reason={decision.reason}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
