# gRPC client для загрузки исторических свечей из Finam

from datetime import datetime
from finam_client import FinamClient


class FinamHistoryClient:

    def __init__(self):
        self.client = FinamClient()

    # data/finam_history_client.py
    from finam_client import FinamClient

    class FinamHistoryClient:
        def __init__(self):
            # Русский коммент: используем единый FinamClient через shim finam_client.py
            self.client = FinamClient()

        def get_candles(self, symbol, interval, start, end):
            """
            Русский коммент:
            Унифицированный метод: пробуем get_bars(), если нет — пробуем get_candles().
            Возвращаем список dict: timestamp/close/volume.
            """
            if hasattr(self.client, "get_bars"):
                candles = self.client.get_bars(symbol=symbol, timeframe=interval, start_time=start, end_time=end)
            elif hasattr(self.client, "get_candles"):
                candles = self.client.get_candles(symbol=symbol, interval=interval, start=start, end=end)
            else:
                raise AttributeError("FinamClient has no get_bars/get_candles")

            out = []
            for c in candles:
                # Русский коммент: максимально “мягкая” нормализация под разные proto/модели
                ts = getattr(c, "timestamp", None) or getattr(c, "time", None) or getattr(c, "ts", None)

                close = getattr(c, "close", None)
                if hasattr(close, "value"):
                    close = close.value
                close = float(close) if close is not None else None

                vol = getattr(c, "volume", None)
                if hasattr(vol, "value"):
                    vol = vol.value
                vol = float(vol) if vol is not None else None

                out.append({"timestamp": ts, "close": close, "volume": vol})
            return out