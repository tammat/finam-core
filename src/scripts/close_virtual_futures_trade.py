# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse

from finam_core.analytics.trade_outcome_reporter import TradeOutcomeReporter
from finam_core.notifications.trade_signal_notifier import TradeSignalNotifier


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", required=True)
    parser.add_argument("--side", required=True, choices=["BUY", "SELL"])
    parser.add_argument("--entry-price", type=float, required=True)
    parser.add_argument("--exit-price", type=float, required=True)
    parser.add_argument("--qty", type=float, default=1.0)
    parser.add_argument("--stop-loss", type=float, required=True)
    parser.add_argument("--take-profit", type=float, required=True)
    parser.add_argument("--reason", default="manual_close")
    args = parser.parse_args()

    reporter = TradeOutcomeReporter(TradeSignalNotifier())

    outcome = reporter.analyze(
        symbol=args.symbol,
        side=args.side,
        entry_price=args.entry_price,
        exit_price=args.exit_price,
        qty=args.qty,
        stop_loss=args.stop_loss,
        take_profit=args.take_profit,
        reason=args.reason,
    )

    reporter.send_outcome(outcome)

    print(
        f"VIRTUAL_TRADE_CLOSED symbol={outcome.symbol} side={outcome.side} "
        f"entry={outcome.entry_price} exit={outcome.exit_price} "
        f"pnl={outcome.pnl} r={outcome.r_multiple} result={outcome.result}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
