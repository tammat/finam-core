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
    # signal candle = prev
    # execution candle = cur
    # убираем look-ahead bias.

    for prev, cur in zip(events[:-1], events[1:]):
        side = "BUY" if prev.close >= prev.open else "SELL"
        exit_side = "SELL" if side == "BUY" else "BUY"

        replay_id = f"{args.campaign_id}:{args.symbol}:{args.timeframe}:{args.strategy}"

        for fill_side, price, ts, role in [
            (side, cur.open, cur.ts, "entry"),
            (exit_side, cur.close, cur.ts, "exit"),
        ]:
            payload = {
                "signal_id": f"{args.campaign_id}-{args.symbol}-{role}-{fills}",
                "strategy": args.strategy,
                "source": "moex_external_replay",
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

    print(
        f"EXTERNAL_REPLAY_PIPELINE_OK campaign_id={args.campaign_id} "
        f"symbol={args.symbol} events={len(events)} fills={fills}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
