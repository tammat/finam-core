# src/scripts/test_order_limit.py
import os
from finam_core.adapters.grpc.orders import FinamOrdersClient

ACCOUNT_ID = "1943312"

def main():
    c = FinamOrdersClient()
    # Русский коммент: SYMBOL из окружения; дефолт — NGH6@RTSX
    symbol = os.getenv("SYMBOL") or "NGH6@RTSX"
    qty = 10
    limit_price = 130.00

    dry = os.getenv("DRY_RUN", "1") != "0"
    if dry:
        print("DRY_RUN=1: will NOT send order")
        req = c.build_limit_order(symbol, "BUY", qty, limit_price, ACCOUNT_ID)
        print("ORDER REQUEST:", req)
        return

    c.place_limit_order(symbol, "BUY", qty, limit_price, ACCOUNT_ID)

if __name__ == "__main__":
    main()