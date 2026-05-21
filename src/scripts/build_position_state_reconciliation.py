from __future__ import annotations

import argparse

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.portfolio.position_state_reconciliation_repository import (
    PositionStateReconciliationRepository,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--migrate", action="store_true")
    parser.add_argument("--save", action="store_true")
    parser.add_argument("--show-ok", action="store_true")
    args = parser.parse_args()

    repo = PositionStateReconciliationRepository(build_psycopg_url())

    if args.migrate or args.save:
        repo.migrate()

    decisions = repo.build_decisions()

    if args.save:
        repo.save(decisions)

    critical = 0
    mismatch = 0

    for item in decisions:
        if item.status != "OK":
            mismatch += 1
        if item.severity == "CRITICAL":
            critical += 1

        if item.status != "OK" or args.show_ok:
            print(
                "POSITION_STATE_RECONCILIATION "
                f"symbol={item.symbol} " f"name={item.display_name} "
                f"broker_qty={item.broker_qty} "
                f"local_qty={item.local_qty} "
                f"lifecycle_qty={item.lifecycle_qty} "
                f"managed_qty={item.managed_qty} "
                f"status={item.status} "
                f"severity={item.severity} "
                f"reason={item.reason}",
                flush=True,
            )

    print(
        "POSITION_STATE_RECONCILIATION_SUMMARY "
        f"total={len(decisions)} "
        f"mismatch={mismatch} "
        f"critical={critical}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
