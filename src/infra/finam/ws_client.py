import asyncio
import json
import os
import websockets

WS_URL = "wss://api.finam.ru/ws"

async def main():
    token = os.environ["FINAM_TOKEN"]
    account_id = os.environ.get("FINAM_ACCOUNT_ID")

    async with websockets.connect(WS_URL) as ws:
        # 1) ждём handshake
        msg = await ws.recv()
        print(msg)

        # 2) подписка (лучше ACCOUNT — часто даёт данные сразу)
        if account_id:
            req = {
                "action": "SUBSCRIBE",
                "type": "ACCOUNT",
                "data": {"account_id": "11022025"},
                "token": token,
            }
            await ws.send(json.dumps(req))

        # 3) читаем поток
        while True:
            msg = await ws.recv()
            try:
                data = json.loads(msg)
            except Exception:
                print("RAW:", msg)
                continue

            print("TYPE:", data.get("type"), data)

if __name__ == "__main__":
    asyncio.run(main())