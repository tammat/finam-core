from __future__ import annotations

import argparse
import json
import uuid

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.strategy.futures.ng_conservative_breakout_m1 import NgConservativeBreakoutM1
from finam_core.research.futures_session_classifier import classify_futures_session
from finam_core.research.ng_regime_classifier import classify_ng_regime
from finam_core.research.ng_regime_v2 import NgRegimeFeaturesV2, classify_ng_regime_v2


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


def calc_replay_features(bars: list[dict], atr_window: int = 14, ema_window: int = 20) -> dict:
    """Русский комментарий: рассчитывает признаки режима для replay-сделки NG."""
    if len(bars) < max(atr_window, ema_window) + 2:
        return {
            "atr_percent": 0.0,
            "atr_expansion": 1.0,
            "range_expansion": 1.0,
            "ema_slope": 0.0,
            "compression_score": 0.0,
            "breakout_strength": 1.0,
            "regime": "UNKNOWN",
            "regime_v2": "UNKNOWN",
        }

    recent = bars[-max(atr_window * 2, ema_window * 2) - 1:]
    closes = [float(x["close"]) for x in recent]
    highs = [float(x["high"]) for x in recent]
    lows = [float(x["low"]) for x in recent]

    true_ranges = []
    for prev, cur in zip(recent, recent[1:]):
        high = float(cur["high"])
        low = float(cur["low"])
        prev_close = float(prev["close"])
        true_ranges.append(max(high - low, abs(high - prev_close), abs(low - prev_close)))

    current_atr_values = true_ranges[-atr_window:]
    previous_atr_values = true_ranges[-atr_window * 2:-atr_window]

    current_atr = sum(current_atr_values) / len(current_atr_values) if current_atr_values else 0.0
    previous_atr = sum(previous_atr_values) / len(previous_atr_values) if previous_atr_values else current_atr

    close = closes[-1]
    atr_percent = (current_atr / close) * 100 if close else 0.0
    atr_expansion = current_atr / previous_atr if previous_atr else 1.0

    ema_half = max(2, ema_window // 2)
    ema_old = sum(closes[-ema_window:-ema_half]) / max(1, len(closes[-ema_window:-ema_half]))
    ema_new = sum(closes[-ema_half:]) / max(1, len(closes[-ema_half:]))
    ema_slope = ((ema_new - ema_old) / ema_old) * 100 if ema_old else 0.0

    current_range = max(highs[-ema_window:]) - min(lows[-ema_window:])
    previous_range_slice_highs = highs[-ema_window * 2:-ema_window]
    previous_range_slice_lows = lows[-ema_window * 2:-ema_window]
    previous_range = (
        max(previous_range_slice_highs) - min(previous_range_slice_lows)
        if previous_range_slice_highs and previous_range_slice_lows
        else current_range
    )

    range_expansion = current_range / previous_range if previous_range else 1.0

    compression_score = 1.0 - min(1.0, (current_range / close) / 0.02) if close else 0.0

    recent_range_high = max(highs[-ema_window:-1])
    recent_range_low = min(lows[-ema_window:-1])
    if current_atr:
        upside_break = max(0.0, close - recent_range_high) / current_atr
        downside_break = max(0.0, recent_range_low - close) / current_atr
        breakout_strength = max(upside_break, downside_break)
    else:
        breakout_strength = 1.0

    regime = classify_ng_regime(
        atr_percent=atr_percent,
        ema_slope=ema_slope,
        compression_score=compression_score,
    )

    # Русский комментарий: session_bucket будет добавлен ниже в replay loop.
    regime_v2 = classify_ng_regime_v2(
        NgRegimeFeaturesV2(
            atr_percent=atr_percent,
            atr_expansion=atr_expansion,
            range_expansion=range_expansion,
            ema_slope=ema_slope,
            compression_score=compression_score,
            breakout_strength=breakout_strength,
            session_bucket="UNKNOWN",
        )
    )

    return {
        "atr_percent": round(atr_percent, 6),
        "atr_expansion": round(atr_expansion, 6),
        "range_expansion": round(range_expansion, 6),
        "ema_slope": round(ema_slope, 6),
        "compression_score": round(compression_score, 6),
        "breakout_strength": round(breakout_strength, 6),
        "regime": regime,
        "regime_v2": regime_v2,
    }

def calc_realized_pnl(*, side: str, entry: float, exit_price: float, qty: float) -> float:
    """Русский комментарий: считает PnL replay-сделки без комиссий."""
    if side == "BUY":
        return (exit_price - entry) * qty
    return (entry - exit_price) * qty


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", default="NGM6@RTSX,NGN6@RTSX,NGQ6@RTSX")
    parser.add_argument("--timeframe", default="M1")
    parser.add_argument("--limit", type=int, default=5000)
    parser.add_argument("--qty", type=float, default=1.0)
    parser.add_argument("--max-hold-bars", type=int, default=12)
    args = parser.parse_args()

    symbols = [x.strip() for x in args.symbols.split(",") if x.strip()]
    strategy_name = "NG_CONSERVATIVE_BREAKOUT_M1"

    total_signals = 0
    total_trades = 0

    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:
            ensure_tables(cur)

            for symbol in symbols:
                bars = load_bars(cur, symbol, args.timeframe.upper(), args.limit)
                strategy = NgConservativeBreakoutM1(symbol=symbol)

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

                            realized_pnl = calc_realized_pnl(
                                side=position["side"],
                                entry=position["entry"],
                                exit_price=exit_price,
                                qty=args.qty,
                            )

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
                                    "realized_pnl": round(realized_pnl, 8),
                                    "atr_percent": position["features"]["atr_percent"],
                                    "regime_v2": position["features"]["regime_v2"],
                                    "breakout_strength": position["features"]["breakout_strength"],
                                    "range_expansion": position["features"]["range_expansion"],
                                    "atr_expansion": position["features"]["atr_expansion"],
                                    "ema_slope": position["features"]["ema_slope"],
                                    "compression_score": position["features"]["compression_score"],
                                    "regime": position["features"]["regime"],
                                    "session_bucket": position["session_bucket"],
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

                    features = calc_replay_features(window)
                    session_bucket = classify_futures_session(bar["ts"])

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
                            "atr_percent": features["atr_percent"],
                            "regime_v2": features["regime_v2"],
                            "breakout_strength": features["breakout_strength"],
                            "range_expansion": features["range_expansion"],
                            "atr_expansion": features["atr_expansion"],
                            "ema_slope": features["ema_slope"],
                            "compression_score": features["compression_score"],
                            "regime": features["regime"],
                            "session_bucket": session_bucket,
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
                        "features": features,
                        "session_bucket": session_bucket,
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
