from __future__ import annotations

from marketcore.research.execution.dto.signal import StrategySignal
from marketcore.research.execution.interfaces.data_provider import MarketBars


class VolatilityBreakoutEngine:
    engine_name = "VOLATILITY_BREAKOUT_ENGINE_V1"

    def execute(
        self,
        market_data: MarketBars,
        parameters: dict | None = None,
    ) -> list[StrategySignal]:
        params = parameters or {}
        lookback = int(params.get("lookback", 20))
        threshold = float(params.get("threshold", 0.0))

        lookback = max(2, min(lookback, 500))
        bars = market_data.bars

        if len(bars) <= lookback:
            return []

        signals: list[StrategySignal] = []

        for i in range(lookback, len(bars)):
            window = bars[i - lookback:i]
            bar = bars[i]

            prev_high = max(x.high for x in window)
            prev_low = min(x.low for x in window)

            direction = "FLAT"
            if bar.close > prev_high + threshold:
                direction = "BUY"
            elif bar.close < prev_low - threshold:
                direction = "SELL"

            if direction == "FLAT":
                continue

            signals.append(
                StrategySignal(
                    signal_ts=bar.ts,
                    direction=direction,
                    price=bar.close,
                    confidence=0.50,
                    metadata={
                        "engine_name": self.engine_name,
                        "lookback": lookback,
                        "threshold": threshold,
                        "prev_high": prev_high,
                        "prev_low": prev_low,
                    },
                )
            )

        return signals
