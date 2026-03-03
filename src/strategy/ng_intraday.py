import pandas as pd
import numpy as np
from typing import Optional
from strategy.base_strategy import BaseStrategy, Signal


class NGIntradayStrategy(BaseStrategy):

    def __init__(self, symbol: str):
        super().__init__(symbol)
        self.df = pd.DataFrame()

    def on_bar(self, bar) -> Optional[Signal]:

        self.df = pd.concat([self.df, pd.DataFrame([bar])])

        if len(self.df) < 60:
            return None

        df = self.df

        # Indicators
        df["ema20"] = df["close"].ewm(span=20).mean()
        df["ema50"] = df["close"].ewm(span=50).mean()

        df["tr"] = np.maximum(
            df["high"] - df["low"],
            np.maximum(
                abs(df["high"] - df["close"].shift()),
                abs(df["low"] - df["close"].shift())
            )
        )

        df["atr"] = df["tr"].rolling(14).mean()
        df["atr_ma"] = df["atr"].rolling(50).mean()

        last = df.iloc[-1]
        prev = df.iloc[-2]

        # Regime filter
        breakout_allowed = last["atr"] > last["atr_ma"]

        # LONG trend pullback
        if (
            breakout_allowed
            and last["ema20"] > last["ema50"]
            and last["close"] > last["ema20"]
            and prev["low"] <= prev["ema20"]
        ):
            entry = last["close"]
            stop = entry - 1.2 * last["atr"]
            take = entry + 2.2 * last["atr"]

            return Signal(
                symbol=self.symbol,
                side="LONG",
                entry=entry,
                stop=stop,
                take=take,
                reason="trend_pullback"
            )

        # SHORT trend pullback
        if (
            breakout_allowed
            and last["ema20"] < last["ema50"]
            and last["close"] < last["ema20"]
            and prev["high"] >= prev["ema20"]
        ):
            entry = last["close"]
            stop = entry + 1.2 * last["atr"]
            take = entry - 2.2 * last["atr"]

            return Signal(
                symbol=self.symbol,
                side="SHORT",
                entry=entry,
                stop=stop,
                take=take,
                reason="trend_pullback"
            )

        return None