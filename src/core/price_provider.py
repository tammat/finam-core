class PriceProvider:
    """
    Interface for market price injection.
    """

    def get_price(self, symbol: str) -> float:
        raise NotImplementedError


class InMemoryPriceProvider(PriceProvider):
    """
    Simple in-memory provider for tests.
    """

    def __init__(self):
        self._prices = {}

    def set_price(self, symbol: str, price: float):
        self._prices[symbol] = price

    def get_price(self, symbol: str) -> float:
        return self._prices.get(symbol, None)