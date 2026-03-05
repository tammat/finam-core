import os
from finam_core.adapters.grpc.orders import FinamOrdersClient

ACCOUNT_ID = "1943312"

def main():
    c = FinamOrdersClient()
    symbol = os.getenv("SYM", "SVETP@MISX")
    qty = float(os.getenv("QTY", "10"))
    price = float(os.getenv("PRICE", "130.00"))

    print("SENDING ONE LIMIT ORDER:", symbol, qty, price)
    resp = c.place_limit_order(symbol, "BUY", qty, price, ACCOUNT_ID)
    print("RESPONSE:", resp)

if __name__ == "__main__":
    main()
