class PortfolioManager:

    def __init__(self, position_manager, initial_cash=0):

        self.positions = position_manager

        self.cash = float(initial_cash)

        self.market_prices = {}

        self.equity = float(initial_cash)

        self.max_equity = float(initial_cash)

    # ------------------------------------------------

    def update_price(self, symbol, price):

        if price is None:
            return

        self.market_prices[symbol] = price

    # ------------------------------------------------

    def get_unrealized_pnl(self):

        pnl = 0.0

        for symbol, pos in self.positions.positions.items():

            qty = pos["qty"]
            avg_price = pos["avg_price"]

            price = self.market_prices.get(symbol)

            if price is None:
                continue

            pnl += (price - avg_price) * qty

        return pnl

    # ------------------------------------------------

    def get_equity(self):

        unrealized = self.get_unrealized_pnl()

        self.equity = self.cash + unrealized

        if self.equity > self.max_equity:
            self.max_equity = self.equity

        return self.equity

    # ------------------------------------------------

    def get_drawdown(self):

        if self.max_equity == 0:
            return 0

        return (self.equity - self.max_equity) / self.max_equity

    # ------------------------------------------------

    def get_context(self):

        equity = self.get_equity()

        drawdown = self.get_drawdown()

        context = {
            "portfolio_value": equity,
            "realized_pnl": self.positions.realized_pnl,
            "daily_realized_pnl": self.positions.realized_pnl,
            "drawdown": drawdown
        }

        return context