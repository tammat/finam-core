from dataclasses import dataclass
from domain.risk.risk_decision import RiskDecision

@dataclass
class ExposureRule:
    max_total_exposure: float = 0.6      # 60% портфеля
    max_symbol_exposure: float = 0.2     # 20% на один инструмент

    def evaluate(self, intent, pm) -> RiskDecision:
        # Продающие сделки нагрузку уменьшают — не блокируем
        side = getattr(intent, "side", "").upper()
        if side != "BUY":
            return RiskDecision(allowed=True)

        qty = float(getattr(intent, "qty", 0.0))
        price = float(getattr(intent, "price", 0.0))
        symbol = getattr(intent, "symbol", None)

        if not symbol or qty <= 0 or price <= 0:
            return RiskDecision(allowed=True)

        equity = float(pm.total_equity())
        if equity <= 0:
            return RiskDecision(allowed=False, reason="Нулевая стоимость портфеля")

        planned = qty * price

        # текущая нагрузка по инструменту
        pos = pm.positions.get(symbol)
        current_symbol = 0.0
        if pos is not None:
            current_symbol = abs(float(getattr(pos, "qty", 0.0)) * float(getattr(pos, "mark_price", 0.0)))

        # текущая совокупная нагрузка
        current_total = 0.0
        for p in pm.positions.values():
            q = float(getattr(p, "qty", 0.0))
            mp = float(getattr(p, "mark_price", 0.0))
            current_total += abs(q * mp)

        next_symbol_share = (current_symbol + planned) / equity
        next_total_share = (current_total + planned) / equity

        if next_symbol_share > self.max_symbol_exposure:
            return RiskDecision(
                allowed=False,
                reason=f"Превышен лимит на инструмент: {next_symbol_share:.2%} > {self.max_symbol_exposure:.2%}",
            )

        if next_total_share > self.max_total_exposure:
            return RiskDecision(
                allowed=False,
                reason=f"Превышен общий лимит: {next_total_share:.2%} > {self.max_total_exposure:.2%}",
            )

        return RiskDecision(allowed=True)