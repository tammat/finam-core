from __future__ import annotations

import argparse
import json
import uuid

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.strategy.futures.ng_conservative_breakout import NgConservativeBreakout


def load_bars(cur, symbol: str, timeframe: str, limit: int):
    cur.execute("""
        SELECT ts, open, high, low, close, volume
        FROM market_bars
        WHERE symbol=%s
          AND timeframe=%s
        ORDER BY ts
        LIMIT %s
    """, (symbol, timeframe, limit))

    return [
        {
            "ts": row[0],
            "open": float(row[1]),
            "high": float(row[2]),
            "low": float(row[3]),
            "close": float(row[4]),
            "volume": float(row[5] or 0),
        }
        for row in cur.fetchall()
    ]


def ensure_tables(cur) -> None:
    cur.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id BIGSERIAL PRIMARY KEY,
            symbol TEXT NOT NULL,
            side TEXT NOT NULL,
            qty NUMERIC NOT NULL,
            price NUMERIC NOT NULL,
            trade_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            strategy TEXT,
            timeframe TEXT,
            trade_source TEXT NOT NULL DEFAULT 'paper',
            payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
    """)


def insert_trade(cur, *, symbol, side, qty, price, ts, strategy, timeframe, payload):
    cur.execute("""
        INSERT INTO trades (
            symbol, side, qty, price, ts,
            strategy, timeframe, trade_source, payload, created_at
        )
        VALUES (%s,%s,%s,%s,%s,%s,%s,'paper',%s::jsonb,now())
    """, (
        symbol,
        side,
        qty,
        price,
        ts,
        strategy,
        timeframe,
        json.dumps(payload, ensure_ascii=False),
    ))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="NGM6@RTSX,NGN6@RTSX,NGQ6@RTSX")
    parser.add_argument("--timeframe", default="M5")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--qty", type=float, default=1.0)
    parser.add_argument("--max-hold-bars", type=int, default=12)
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    strategy_name = "NG_CONSERVATIVE_BREAKOUT"

    total_signals = 0
    total_trades = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)

            for symbol in symbols:
                bars = load_bars(cur, symbol, args.timeframe.upper(), args.limit)
                strategy = NgConservativeBreakout(symbol=symbol, timeframe=args.timeframe.upper())

                position = None
                signals = 0
                trades = 0

                for i in range(40, len(bars)):
                    window = bars[: i + 1]
                    bar = bars[i]

                    if position is not None:
                        position["bars_held"] += 1

                        exit_reason = None
                        exit_price = None

                        if position["side"] == "BUY":
                            if bar["low"] <= position["stop"]:
                                exit_reason = "STOP"
                                exit_price = position["stop"]
                            elif bar["high"] >= position["take"]:
                                exit_reason = "TAKE"
                                exit_price = position["take"]
                        else:
                            if bar["high"] >= position["stop"]:
                                exit_reason = "STOP"
                                exit_price = position["stop"]
                            elif bar["low"] <= position["take"]:
                                exit_reason = "TAKE"
                                exit_price = position["take"]

                        if exit_reason is None and position["bars_held"] >= args.max_hold_bars:
                            exit_reason = "TIME_EXIT"
                            exit_price = bar["close"]

                        if exit_reason:
                            exit_side = "SELL" if position["side"] == "BUY" else "BUY"
                            chain_id = position["chain_id"]

                            insert_trade(
                                cur,
                                symbol=symbol,
                                side=exit_side,
                                qty=args.qty,
                                price=exit_price,
                                ts=bar["ts"],
                                strategy=strategy_name,
                                timeframe=args.timeframe.upper(),
                                payload={
                                    "chain_id": chain_id,
                                    "role": "exit",
                                    "exit_reason": exit_reason,
                                    "entry_price": position["entry"],
                                    "strategy": strategy_name,
                                    "timeframe": args.timeframe.upper(),
                                },
                            )
                            trades += 1
                            position = None

                        continue

                    signal = strategy.on_bars(window)
                    if signal is None:
                        continue

                    chain_id = str(uuid.uuid4())
                    signals += 1

                    insert_trade(
                        cur,
                        symbol=symbol,
                        side=signal.side,
                        qty=args.qty,
                        price=signal.entry_price,
                        ts=bar["ts"],
                        strategy=strategy_name,
                        timeframe=args.timeframe.upper(),
                        payload={
                            "chain_id": chain_id,
                            "role": "entry",
                            "reason": signal.reason,
                            "stop_price": signal.stop_price,
                            "take_price": signal.take_price,
                            "confidence": signal.confidence,
                            "strategy": strategy_name,
                            "timeframe": args.timeframe.upper(),
                        },
                    )

                    position = {
                        "chain_id": chain_id,
                        "side": signal.side,
                        "entry": signal.entry_price,
                        "stop": signal.stop_price,
                        "take": signal.take_price,
                        "bars_held": 0,
                    }
                    trades += 1

                print(
                    f"NG_REPLAY_OK symbol={symbol} bars={len(bars)} signals={signals} trades={trades}",
                    flush=True,
                )

                total_signals += signals
                total_trades += trades

        conn.commit()

    print(
        f"NG_REPLAY_SUMMARY symbols={len(symbols)} signals={total_signals} trades={total_trades}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
