import asyncio

from finam_core.app.bootstrap import bootstrap


async def main():

    pipeline, event_bus, gateway, feed = await bootstrap()

    print("Trading system started")

    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    asyncio.run(main())