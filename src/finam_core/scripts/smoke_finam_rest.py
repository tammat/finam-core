from __future__ import annotations

import os
from finam_core.dotenv import load_dotenv

from finam_core.infra.brokers.finam_rest import FinamRestBrokerAdapter, FinamRestConfig, FinamRestError


def main() -> int:
    load_dotenv()

    cfg = FinamRestConfig.from_env()
    broker = FinamRestBrokerAdapter(cfg)
    broker.start()

    try:
        print("BASE:", cfg.base_url)

        # 1) Accounts
        try:
            acc = broker.get_accounts()
            print("ACCOUNTS:", acc[:3], f"(total={len(acc)})")
        except FinamRestError as e:
            print("ACCOUNTS ERROR:", e)

        # 2) Portfolio/Positions
        account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
        if account_id:
            try:
                pos = broker.get_positions(account_id)
                print("POSITIONS:", pos[:3], f"(total={len(pos)})")
            except FinamRestError as e:
                print("POSITIONS ERROR:", e)
        else:
            print("FINAM_ACCOUNT_ID is empty -> skip positions test")

        return 0
    finally:
        broker.stop()


if __name__ == "__main__":
    raise SystemExit(main())