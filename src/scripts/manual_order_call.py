from finam_core.adapters.grpc.orders import FinamOrdersClient

ACCOUNT_ID = "1943312"

def main():
    c = FinamOrdersClient()
    # GAZP: 1 лот = 10 акций -> пробуем 10
    c.place_market_order("GAZP@MISX", "BUY", 10, ACCOUNT_ID)

if __name__ == "__main__":
    main()
