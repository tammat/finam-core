from __future__ import annotations

from decimal import Decimal

from marketcore.market.dto import MarketSnapshotDTO


class PaperCostCalculator:
    def calculate_net_pnl(
        self,
        gross_pnl: Decimal,
        entry_price: Decimal,
        snapshot: MarketSnapshotDTO,
    ) -> dict[str, Decimal]:
        commission = snapshot.cost.commission_fixed + abs(entry_price * snapshot.cost.commission_percent)
        exchange_fee = snapshot.cost.exchange_fee_fixed
        clearing_fee = snapshot.cost.clearing_fee_fixed
        slippage = snapshot.cost.slippage_fixed

        net_trading_pnl = gross_pnl - commission - exchange_fee - clearing_fee - slippage
        estimated_tax = net_trading_pnl * snapshot.tax.tax_rate if net_trading_pnl > 0 else Decimal("0")
        net_after_tax = net_trading_pnl - estimated_tax

        return {
            "commission": commission,
            "exchange_fee": exchange_fee,
            "clearing_fee": clearing_fee,
            "slippage": slippage,
            "net_trading_pnl": net_trading_pnl,
            "estimated_tax": estimated_tax,
            "net_after_tax": net_after_tax,
        }
