# -*- coding: utf-8 -*-
import os

from finam_core.adapters.grpc.orders import FinamOrdersClient

ACCOUNT_ID = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID") or "1943312"


def main() -> None:
    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
    side = os.getenv("SIDE") or "BUY"
    qty = float(os.getenv("QTY") or "10")

    c = FinamOrdersClient()
    c.place_market_order(symbol, side, qty, ACCOUNT_ID)


if __name__ == "__main__":
    main()
