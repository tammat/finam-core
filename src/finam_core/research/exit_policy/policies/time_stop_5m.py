from datetime import timedelta

from finam_core.research.exit_policy.policy_base import (
    ClosedTradeInput,
    ExitPolicy,
    VirtualExitResult,
)


class TimeStop5mPolicy(ExitPolicy):
    name = "TIME_STOP_5M"

    def simulate(self, trade: ClosedTradeInput) -> VirtualExitResult:
        virtual_exit_ts = min(trade.exit_ts, trade.entry_ts + timedelta(minutes=5))

        return VirtualExitResult(
            policy_name=self.name,
            trade_id=trade.trade_id,
            virtual_exit_ts=virtual_exit_ts,
            virtual_exit_price=trade.exit_price,
            virtual_net_pnl=trade.net_pnl,
            reason="scaffold_uses_real_exit_price_until_market_bar_replay_v1",
        )
