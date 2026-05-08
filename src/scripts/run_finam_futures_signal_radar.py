# -*- coding: utf-8 -*-
from __future__ import annotations

from finam_core.data.finam_futures_signal_radar import FinamFuturesSignalRadar
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier


def main() -> int:
    radar = FinamFuturesSignalRadar()
    notifier = TradeSignalNotifier()

    # Русский комментарий: пока smoke/demo. Следующий шаг — заменить на live Finam MarketData.
    demo_market = [
        {"symbol": "BRN6@RTSX", "last": 64.20, "atr": 0.85, "trend_score": 0.62},
        {"symbol": "NGQ6@RTSX", "last": 3.48, "atr": 0.11, "trend_score": -0.71},
        {"symbol": "SiM6@RTSX", "last": 93450.0, "atr": 620.0, "trend_score": 0.44},
    ]

    total = 0

    for item in demo_market:
        signal = radar.build_signal(
            symbol=item["symbol"],
            last=float(item["last"]),
            atr=float(item["atr"]),
            trend_score=float(item["trend_score"]),
        )

        if signal is None:
            continue

        print(
            f"FUTURES_SIGNAL {signal.symbol} {signal.side} "
            f"entry={signal.entry} sl={signal.stop_loss} tp={signal.take_profit}",
            flush=True,
        )

        notifier.send_signal(
            symbol=signal.symbol,
            side=signal.side,
            entry=signal.entry,
            stop_loss=signal.stop_loss,
            take_profit=signal.take_profit,
            confidence=signal.confidence,
            regime="futures_signal",
            reason=signal.reason,
        )

        total += 1

    print(f"FUTURES_SIGNAL_SENT total={total}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
