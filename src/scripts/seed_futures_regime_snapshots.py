from __future__ import annotations

import argparse
import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.analytics.regime_snapshot_repository import RegimeSnapshotRepository


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--roots", default="BR,NG,USD")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--max-contracts", type=int, default=3)
    parser.add_argument("--source", default="futures_regime_seed")
    args = parser.parse_args()

    roots = [x.strip() for x in args.roots.split(",") if x.strip()]
    regime_repo = RegimeSnapshotRepository()
    regime_repo.migrate()

    saved = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            for root in roots:
                cur.execute(
                    """
                    SELECT contract_symbol
                    FROM futures_contract_universe
                    WHERE root_symbol=%s
                      AND is_active=TRUE
                      AND status <> 'QUARANTINE'
                    ORDER BY roll_priority, expiration_date NULLS LAST
                    LIMIT %s
                    """,
                    (root, args.max_contracts),
                )

                contracts = [row[0] for row in cur.fetchall()]

                for contract in contracts:
                    regime_repo.save_snapshot(
                        symbol=contract,
                        timeframe=args.timeframe,
                        regime="unknown",
                        trend="unknown",
                        volatility="unknown",
                        atr=0.0,
                        source=args.source,
                    )
                    saved += 1
                    print(
                        "FUTURES_REGIME_SNAPSHOT_SEEDED "
                        f"root={root} symbol={contract} timeframe={args.timeframe}",
                        flush=True,
                    )

    print(f"FUTURES_REGIME_SNAPSHOT_SUMMARY saved={saved}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
