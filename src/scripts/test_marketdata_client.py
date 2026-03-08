import os

# Русский коммент: SYMBOLS — CSV список (например: GAZP@MISX,SBER@MISX)
SYMBOLS = [x.strip() for x in (os.getenv('SYMBOLS') or '').split(',') if x.strip()] or [os.getenv('SYMBOL') or 'NGH6@RTSX']

from finam_core.adapters.grpc.market_data import FinamMarketDataClient


class DummyBus:

    def publish(self, event):
        print(event)


def main():

    bus = DummyBus()

    md = FinamMarketDataClient(bus)

    md.start(SYMBOLS)

    import time
    while True:
        time.sleep(1)


if __name__ == "__main__":
    main()