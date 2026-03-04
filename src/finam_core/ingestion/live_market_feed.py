import asyncio

class LiveMarketFeed:

    def __init__(self, market_client, event_bus):

        self.client = market_client
        self.event_bus = event_bus

        self.queue = asyncio.Queue()

    async def start(self, symbol):

        asyncio.create_task(self._reader(symbol))
        asyncio.create_task(self._dispatcher())

    async def _reader(self, symbol):

        loop = asyncio.get_event_loop()

        def blocking_stream():

            for bar in self.client.subscribe_bars(symbol, 1):
                asyncio.run_coroutine_threadsafe(
                    self.queue.put(bar),
                    loop
                )

        await asyncio.to_thread(blocking_stream)

    async def _dispatcher(self):

        while True:

            bar = await self.queue.get()

            event = {
                "type": "MARKET_BAR",
                "symbol": bar.symbol,
                "price": bar.close,
                "timestamp": bar.timestamp
            }

            self.event_bus.publish(event)