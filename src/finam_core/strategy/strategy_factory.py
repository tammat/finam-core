from __future__ import annotations

from finam_core.strategy.symbol_strategy_map import (
    SYMBOL_STRATEGY_MAP,
    DEFAULT_STRATEGY,
)

from finam_core.strategy.br.br_conservative_breakout import BrConservativeBreakout
from finam_core.strategy.ng.ng_volatility_breakout import NGVolatilityBreakout
from finam_core.strategy.fx.usdrub_regime_strategy import USDRUBRegimeStrategy
from finam_core.strategy.equities.mean_reversion_equity import MeanReversionEquity
from finam_core.strategy.equities.trend_pullback_equity import TrendPullbackEquity
from finam_core.strategy.equities.volatility_breakout_equity import VolatilityBreakoutEquity


class StrategyFactory:

    @staticmethod
    def create(symbol: str, strategy_name: str | None = None):

        strategy_name = strategy_name or SYMBOL_STRATEGY_MAP.get(
            symbol,
            DEFAULT_STRATEGY,
        )

        if strategy_name == "BR_CONSERVATIVE_BREAKOUT":
            return BrConservativeBreakout()

        if strategy_name == "NG_VOLATILITY_BREAKOUT":
            return NGVolatilityBreakout()

        if strategy_name == "USDRUB_REGIME":
            return USDRUBRegimeStrategy()

        if strategy_name == "TREND_PULLBACK_EQUITY":
            return TrendPullbackEquity()

        if strategy_name == "VOLATILITY_BREAKOUT_EQUITY":
            return VolatilityBreakoutEquity()

        return MeanReversionEquity()
