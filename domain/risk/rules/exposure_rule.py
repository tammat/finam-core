from domain.risk.risk_stack import RiskDecision


class ExposureRule:

    def __init__(
        self,
        max_total_exposure: float = 0.6,   # 60%
        max_symbol_exposure: float = 0.2,  # 20%
    ):
        self.max_total_exposure = max_total_exposure
        self.max_symbol_exposure = max_symbol_exposure

    def evaluate(self, intent, portfolio):

        equity = portfolio.total_equity()

        if equity <= 0:
            return RiskDecision(False, "zero equity")

        # ---- Текущая общая нагрузка ----
        total_exposure = sum(
            abs(pos.qty * pos.mark_price)
            for pos in portfolio.positions.values()
        )

        # ---- Симуляция после сделки ----
        current_position = portfolio.positions.get(intent.symbol)

        current_qty = current_position.qty if current_position else 0.0
        current_price = current_position.mark_price if current_position else intent.price

        new_qty = current_qty + (intent.qty if intent.side == "BUY" else -intent.qty)

        new_symbol_exposure = abs(new_qty * intent.price)

        # новая общая нагрузка
        simulated_total = total_exposure - abs(current_qty * current_price) + new_symbol_exposure

        # ---- Проверка общей нагрузки ----
        if simulated_total / equity > self.max_total_exposure:
            return RiskDecision(False, "total exposure limit")

        # ---- Проверка нагрузки на инструмент ----
        if new_symbol_exposure / equity > self.max_symbol_exposure:
            return RiskDecision(False, "symbol exposure limit")

        return RiskDecision(True)