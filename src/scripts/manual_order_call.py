# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os

from dotenv import load_dotenv

from finam_core.adapters.grpc.orders_client import FinamOrdersClient

load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"])
    parser.add_argument("--qty", required=True, type=float)
    parser.add_argument("--price", required=False, type=float, default=None)
    args = parser.parse_args()

    os.environ.setdefault("EXECUTION_MODE", "real")

    client = FinamOrdersClient()
    result = client.place_market_order(
        symbol=args.symbol,
        side=args.side,
        qty=args.qty,
        price=args.price,
    )

    print("MANUAL_ORDER_CALL_RESULT")
    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
