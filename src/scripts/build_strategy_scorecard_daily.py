from __future__ import annotations

import argparse
from datetime import datetime

from finam_core.analytics.strategy_scorecard_persistence import (
    StrategyScorecardPersistence,
)
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--date",
        required=True,
        help="Дата расчёта scorecard в формате YYYY-MM-DD",
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    trade_date = datetime.strptime(args.date, "%Y-%m-%d").date()

    pg_logger = PostgresLogger()

    persistence = StrategyScorecardPersistence(pg_logger)

    saved = persistence.calculate_and_save_daily(trade_date)

    print(
        f"STRATEGY_SCORECARD_DAILY_OK date={trade_date} saved={saved}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
