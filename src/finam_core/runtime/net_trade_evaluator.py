from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NetTradeEvaluation:
    gross_profit: float
    gross_loss: float

    commissions: float
    estimated_tax: float
    slippage_cost: float

    net_take_profit: float
    net_stop_loss: float

    expected_value: float
    expected_value_pct: float


class NetTradeEvaluator:
    """Русский комментарий: считает чистую ожидаемую доходность сделки."""

    def evaluate(
        self,
        *,
        entry_price: float,
        stop_loss: float,
        take_profit: float,
        qty: int,

        probability_tp: float,
        probability_sl: float,

        commission_pct: float = 0.0004,
        tax_pct: float = 0.13,
        slippage_pct: float = 0.0005,
    ) -> NetTradeEvaluation:

        gross_profit = max(
            (take_profit - entry_price) * qty,
            0.0,
        )

        gross_loss = max(
            (entry_price - stop_loss) * qty,
            0.0,
        )

        turnover = (
            entry_price * qty
            + take_profit * qty
        )

        commissions = turnover * commission_pct

        slippage_cost = turnover * slippage_pct

        taxable_profit = max(
            gross_profit - commissions,
            0.0,
        )

        estimated_tax = taxable_profit * tax_pct

        net_take_profit = (
            gross_profit
            - commissions
            - estimated_tax
            - slippage_cost
        )

        net_stop_loss = (
            gross_loss
            + commissions
            + slippage_cost
        )

        expected_value = (
            probability_tp * net_take_profit
            -
            probability_sl * net_stop_loss
        )

        capital_used = max(entry_price * qty, 1.0)

        expected_value_pct = (
            expected_value / capital_used
        ) * 100.0

        return NetTradeEvaluation(
            gross_profit=round(gross_profit, 2),
            gross_loss=round(gross_loss, 2),

            commissions=round(commissions, 2),
            estimated_tax=round(estimated_tax, 2),
            slippage_cost=round(slippage_cost, 2),

            net_take_profit=round(net_take_profit, 2),
            net_stop_loss=round(net_stop_loss, 2),

            expected_value=round(expected_value, 2),
            expected_value_pct=round(expected_value_pct, 4),
        )
