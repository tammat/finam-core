from __future__ import annotations

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.manual.broker_manual_trade_sync import BrokerManualTradeSync


def main() -> int:
    sync = BrokerManualTradeSync(build_psycopg_url())
    sync.migrate()
    inserted = sync.sync_from_broker_order_snapshots()

    print(
        "BROKER_MANUAL_TRADES_SYNC_OK "
        f"inserted={inserted}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
