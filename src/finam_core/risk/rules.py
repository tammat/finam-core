class MaxPositionSizeRule:
    def __init__(self, max_qty: float):
        self.max_qty = max_qty

    def check(self, symbol, current_qty, order_qty):
        projected = current_qty + order_qty
        if abs(projected) > self.max_qty:
            return False, "MaxPositionSize"
        return True, None


class MaxExposureRule:
    def __init__(self, max_exposure: float):
        self.max_exposure = max_exposure

    def check(self, portfolio_exposure, order_value):
        if portfolio_exposure + abs(order_value) > self.max_exposure:
            return False, "MaxPortfolioExposure"
        return True, None


class MaxDrawdownRule:
    def __init__(self, max_drawdown: float):
        self.max_drawdown = max_drawdown

    def check(self, current_drawdown):
        if current_drawdown > self.max_drawdown:
            return False, "MaxDrawdown"
        return True, None