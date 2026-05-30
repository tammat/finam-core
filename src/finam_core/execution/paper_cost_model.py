from __future__ import annotations

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class PaperCostBreakdown:
    notional: float
    broker_commission: float
    exchange_commission: float
    min_commission: float
    total_commission: float


class PaperCostModel:
    """
    Русский комментарий:
    Единая модель комиссий для PAPER-сделок.
    v1 учитывает только broker + exchange fee.
    Slippage уже учитывается отдельно в PaperExecutionEngine через fill_price.
    """

    def __init__(
        self,
        *,
        broker_rate: float | None = None,
        exchange_rate: float | None = None,
        min_commission: float | None = None,
    ) -> None:
        self.broker_rate = float(
            os.getenv("PAPER_BROKER_COMMISSION_RATE", "0.0")
            if broker_rate is None
            else broker_rate
        )
        self.exchange_rate = float(
            os.getenv("PAPER_EXCHANGE_COMMISSION_RATE", "0.0")
            if exchange_rate is None
            else exchange_rate
        )
        self.min_commission = float(
            os.getenv("PAPER_MIN_COMMISSION", "0.0")
            if min_commission is None
            else min_commission
        )

    def calculate(self, *, price: float, qty: float) -> PaperCostBreakdown:
        notional = abs(float(price) * float(qty))
        broker_commission = notional * self.broker_rate
        exchange_commission = notional * self.exchange_rate
        raw_total = broker_commission + exchange_commission
        total_commission = max(raw_total, self.min_commission)

        return PaperCostBreakdown(
            notional=notional,
            broker_commission=broker_commission,
            exchange_commission=exchange_commission,
            min_commission=self.min_commission,
            total_commission=total_commission,
        )
