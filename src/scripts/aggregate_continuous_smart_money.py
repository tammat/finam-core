from __future__ import annotations

from finam_core.orderflow.continuous_smart_money_aggregator import ContinuousSmartMoneyAggregator
from finam_core.storage.postgres_logger import PostgresLogger


def main() -> int:
    result = ContinuousSmartMoneyAggregator(PostgresLogger()).aggregate_brent()

    if result is None:
        print("NO_CONTINUOUS_SMART_MONEY_DATA")
        return 0

    print(
        "OK: continuous smart money aggregated "
        f"symbol={result.continuous_symbol} "
        f"sources={','.join(result.source_symbols)} "
        f"score={result.smart_money_score} "
        f"label={result.label}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
