from finam_core.events.event_bus import EventBus
from finam_core.adapters.grpc.market_data import FinamMarketDataClient


class TradingPipeline:
    """
    Pipeline:

    MarketData → Portfolio → Strategy → Risk → Execution
    """

    def __init__(
        self,
        strategy,
        risk_engine,
        execution_engine,
        portfolio_manager,
        symbols,
    ):

        self.bus = EventBus()

        self.strategy = strategy
        self.risk = risk_engine
        self.execution = execution_engine
        self.portfolio = portfolio_manager

        self.symbols = symbols

        self.bus.subscribe("QUOTE", self._on_quote)

        self.marketdata = FinamMarketDataClient(self.bus)

    # ------------------------------------------------

    def _on_quote(self, event):

        symbol = event["symbol"]
        price = event["last"]

        # 1 обновляем цены портфеля

        self.portfolio.update_price(symbol, price)

        # 2 стратегия

        signal = self.strategy.on_quote(event)

        if signal is None:
            return

        # 3 контекст риска

        context = self.portfolio.get_context()

        # 4 проверка риска

        decision = self.risk.evaluate(signal, context)

        if not decision.allow:
            print("RISK BLOCK:", decision.reason)
            return

        # 5 исполнение

        self.execution.execute_signal(signal)
    # ------------------------------------------------

    def start(self):

        self.marketdata.start(self.symbols)