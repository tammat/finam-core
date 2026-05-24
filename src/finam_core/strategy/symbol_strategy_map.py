from __future__ import annotations

SYMBOL_STRATEGY_MAP = {
    # Русский комментарий: Brent futures.
    "BRM6@RTSX": "BR_CONSERVATIVE_BREAKOUT",
    "BRN6@RTSX": "BR_CONSERVATIVE_BREAKOUT",
    "BRQ6@RTSX": "BR_CONSERVATIVE_BREAKOUT",

    # Русский комментарий: Natural Gas futures. Runtime M1-контур актуален для текущего рабочего контракта.
    "NGM6@RTSX": "NG_CONSERVATIVE_BREAKOUT_M1",
    "NGN6@RTSX": "NG_CONSERVATIVE_BREAKOUT_M1",
    "NGQ6@RTSX": "NG_CONSERVATIVE_BREAKOUT_M1",

    # Русский комментарий: USD/RUB futures используется как regime/confirmation layer.
    "USDRUBF@RTSX": "USDRUB_REGIME",

    # Русский комментарий: equities.
    "LKOH@MISX": "MEAN_REVERSION_EQUITY",
    "SBERP@MISX": "MEAN_REVERSION_EQUITY",
    "NVTK@MISX": "MEAN_REVERSION_EQUITY",
    "VTBR@MISX": "MEAN_REVERSION_EQUITY",
    "X5@MISX": "MEAN_REVERSION_EQUITY",

    "PLZL@MISX": "TREND_PULLBACK_EQUITY",
    "OZON@MISX": "TREND_PULLBACK_EQUITY",
    "SFIN@MISX": "TREND_PULLBACK_EQUITY",
}

DEFAULT_STRATEGY = "MEAN_REVERSION_EQUITY"
