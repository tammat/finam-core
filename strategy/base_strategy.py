# strategy/base_strategy.py

class BaseStrategy:

    def __init__(self, name: str):
        self.name = name

    def on_market_event(self, event, context):
        """
        event  → MarketEvent
        context → PortfolioContext

        Return:
            None
            or Signal
        """
        raise NotImplementedError

    def on_fill(self, fill_event, context):
        """
        Позволяет стратегии обновлять внутреннее состояние.
        Необязательно для v1.
        """
        pass