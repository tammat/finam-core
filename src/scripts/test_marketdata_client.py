from finam_core.adapters.grpc.market_data import FinamMarketDataClient


class DummyBus:

    def publish(self, event):
        print(event)


def main():

    bus = DummyBus()

    md = FinamMarketDataClient(bus)

    md.start(["GAZP@MISX"])

    import time
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()