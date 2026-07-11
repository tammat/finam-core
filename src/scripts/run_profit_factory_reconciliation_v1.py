from __future__ import annotations

import argparse
import os

import psycopg2

from finam_core.reconciliation.profit_factory import ProfitFactoryReconciliationEngine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Profit Factory reconciliation engine V1")
    parser.add_argument("--dry-run", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    dsn = os.getenv("DATABASE_URL", "postgresql:///finam_core")
    with psycopg2.connect(dsn) as connection:
        result = ProfitFactoryReconciliationEngine(connection).run(dry_run=args.dry_run)

    print(f"run_id={result.run_id}")
    print(f"mode={result.mode}")
    print(f"status={result.status}")
    print(f"source_rows={result.source_rows}")
    print(f"created_rows={result.created_rows}")
    print(f"updated_rows={result.updated_rows}")
    print(f"conflict_rows={result.conflict_rows}")
    print(f"stale_rows={result.stale_rows}")
    print(f"skipped_rows={result.skipped_rows}")
    print("VERDICT=PROFIT_FACTORY_RECONCILIATION_ENGINE_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
