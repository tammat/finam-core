from __future__ import annotations

import argparse
import json
from datetime import timezone

from finam_core.replay.external_replay_adapter import ExternalReplayAdapter
from finam_core.storage.postgres_logger import PostgresLogger


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--campaign-id", required=True)
    p.add_argument("--symbol", required=True)
    p.add_argument("--timeframe", default="D1")
    p.add_argument("--date-from", required=True)
    p.add_argument("--date-to", required=True)
    p.add_argument("--strategy", default="MOEX_SIMPLE_MOMENTUM")
    p.add_argument("--stop-pct", type=float, default=0.015)
    p.add_argument("--take-pct", type=float, default=0.030)
    p.add_argument("--holding-bars", type=int, default=3)
    p.add_argument("--mr-threshold", type=float, default=0.02)
    return p.parse_args()


def main() -> int:
    args = parse_args()
    adapter = ExternalReplayAdapter()
    pg = PostgresLogger()

    events = adapter.load_events(
        symbol=args.symbol,
        timeframe=args.timeframe,
        date_from=args.date_from,
        date_to=args.date_to,
    )

    fills = 0

    # Русский комментарий:
    # signal candle = events[i]
    # entry = events[i+1].open
    # exit = stop/take/holding-period на последующих свечах без look-ahead bias.
    replay_id = f"{args.campaign_id}:{args.symbol}:{args.timeframe}:{args.strategy}"

    i = 0
    while i < len(events) - 1:
        signal_bar = events[i]
        entry_bar = events[i + 1]

        if args.strategy == "MOEX_MEAN_REVERSION_V1":
            # Русский комментарий:
            # mean reversion:
            # если сильное падение -> long.
            drop_pct = (
                float(signal_bar.close) - float(signal_bar.open)
            ) / float(signal_bar.open)

            if drop_pct > -abs(args.mr_threshold):
                i += 1
                continue

            side = "BUY"
            exit_side = "SELL"

        else:
            side = "BUY" if signal_bar.close >= signal_bar.open else "SELL"
            exit_side = "SELL" if side == "BUY" else "BUY"

        entry_price = float(entry_bar.open)
        entry_ts = entry_bar.ts

        if side == "BUY":
            stop_price = entry_price * (1.0 - args.stop_pct)
            take_price = entry_price * (1.0 + args.take_pct)
        else:
            stop_price = entry_price * (1.0 + args.stop_pct)
            take_price = entry_price * (1.0 - args.take_pct)

        exit_price = float(entry_bar.close)
        exit_ts = entry_bar.ts
        exit_reason = "holding_period_exit"

        max_j = min(len(events) - 1, i + max(1, int(args.holding_bars)))

        for j in range(i + 1, max_j + 1):
            bar = events[j]

            if side == "BUY":
                if float(bar.low) <= stop_price:
                    exit_price = stop_price
                    exit_ts = bar.ts
                    exit_reason = "stop_loss"
                    break
                if float(bar.high) >= take_price:
                    exit_price = take_price
                    exit_ts = bar.ts
                    exit_reason = "take_profit"
                    break
            else:
                if float(bar.high) >= stop_price:
                    exit_price = stop_price
                    exit_ts = bar.ts
                    exit_reason = "stop_loss"
                    break
                if float(bar.low) <= take_price:
                    exit_price = take_price
                    exit_ts = bar.ts
                    exit_reason = "take_profit"
                    break

            exit_price = float(bar.close)
            exit_ts = bar.ts

        for fill_side, price, ts, role in [
            (side, entry_price, entry_ts, "entry"),
            (exit_side, exit_price, exit_ts, "exit"),
        ]:
            payload = {
                "signal_id": f"{args.campaign_id}-{args.symbol}-{role}-{fills}",
                "strategy": args.strategy,
                "source": "moex_external_replay_v3",
                "horizon": "HISTORICAL",
                "timeframe": args.timeframe,
                "regime": "MOEX_HISTORY",
                "replay_campaign_id": args.campaign_id,
                "replay_id": replay_id,
                "replay_symbol": args.symbol,
                "replay_timeframe": args.timeframe,
                "replay_strategy": args.strategy,
                "dataset_source": "moex",
                "event_ts": ts.isoformat(),
                "signal_ts": signal_bar.ts.isoformat(),
                "entry_price": entry_price,
                "stop_price": stop_price,
                "take_price": take_price,
                "exit_reason": exit_reason,
                "stop_pct": args.stop_pct,
                "take_pct": args.take_pct,
                "holding_bars": args.holding_bars,
            }

            pg.log_fill(
                symbol=args.symbol,
                side=fill_side,
                qty=1.0,
                price=float(price),
                trade_id=f"{replay_id}:{role}:{fills}",
                execution_type="paper",
                payload=payload,
            )
            fills += 1

        i += max(1, int(args.holding_bars))

    print(
        f"EXTERNAL_REPLAY_PIPELINE_OK campaign_id={args.campaign_id} "
        f"symbol={args.symbol} events={len(events)} fills={fills}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
