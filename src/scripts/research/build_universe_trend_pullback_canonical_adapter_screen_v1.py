#!/usr/bin/env python3
"""
UNIVERSE_TREND_PULLBACK_CANONICAL_ADAPTER_SCREEN_V1

Frozen true-gross OOS screen TREND_PULLBACK_V1 через canonical
postgresql_edge_backtest_adapter_v1.

Запрещено:
- generic build_strategy_execution_runner_v1;
- fallback на другую strategy family;
- execution costs;
- parameter optimization;
- PostgreSQL writes;
- runtime/execution changes.
"""

from __future__ import annotations

import inspect
import json
import os
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path

import psycopg2
import psycopg2.extras

from finam_core.research import (
    postgresql_edge_backtest_adapter_v1 as canonical_adapter,
)


CONFIG_PATH = Path(
    "config/research/"
    "universe_trend_pullback_canonical_adapter_screen_v1.json"
)

STRATEGY_CODE = "TREND_PULLBACK_V1"


@dataclass(frozen=True)
class MarketBar:
    ts: object
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class GrossTrade:
    entry_ts: object
    exit_ts: object
    direction: int
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def gross_metrics(trades: list[GrossTrade]) -> dict:
    values = [
        float(trade.gross_pnl)
        for trade in trades
    ]

    wins = [
        value
        for value in values
        if value > 0
    ]

    losses = [
        value
        for value in values
        if value <= 0
    ]

    gross_win = sum(wins)
    gross_loss = abs(sum(losses))

    if gross_loss > 0:
        profit_factor = (
            gross_win / gross_loss
        )
    elif gross_win > 0:
        profit_factor = gross_win
    else:
        profit_factor = 0.0

    expectancy = (
        sum(values) / len(values)
        if values
        else 0.0
    )

    return {
        "trades": len(values),
        "profit_factor": profit_factor,
        "expectancy": expectancy,
        "gross_pnl": sum(values),
    }


def normalize_signal(value) -> int:
    """
    Нормализует только недвусмысленные canonical signal values.

    Возвращает:
      +1 = long
      -1 = short
       0 = no signal
    """
    if value is None:
        return 0

    if isinstance(value, bool):
        return 1 if value else 0

    if isinstance(value, (int, float)):
        if value > 0:
            return 1
        if value < 0:
            return -1
        return 0

    if isinstance(value, str):
        normalized = value.strip().upper()

        if normalized in {
            "LONG",
            "BUY",
            "UP",
            "1",
        }:
            return 1

        if normalized in {
            "SHORT",
            "SELL",
            "DOWN",
            "-1",
        }:
            return -1

        if normalized in {
            "",
            "NONE",
            "FLAT",
            "HOLD",
            "0",
        }:
            return 0

    raise RuntimeError(
        "ERROR=UNSUPPORTED_CANONICAL_SIGNAL_RETURN "
        f"type={type(value).__name__} value={value!r}"
    )


def call_canonical_signal(
    fn,
    signature,
    bars: list[MarketBar],
    index: int,
    parameters: dict,
    closes: list,
    highs: list,
    lows: list,
    opens: list,
):
    """
    Вызывает trend_pullback_signal только по фактической сигнатуре.

    Поддерживаем только явно распознаваемые argument names.
    При неизвестном контракте fail closed.

    Performance contract:
    signature и OHLC-массивы рассчитываются один раз
    на build_canonical_trades(), а не на каждый бар.
    """
    values = {
        "bars": bars,
        "market_bars": bars,
        "index": index,
        "idx": index,
        "i": index,
        "parameters": parameters,
        "params": parameters,
        "closes": closes,
        "highs": highs,
        "lows": lows,
        "opens": opens,
    }

    kwargs = {}

    for name, parameter in signature.parameters.items():
        if name in values:
            kwargs[name] = values[name]
            continue

        if parameter.default is not inspect.Parameter.empty:
            continue

        raise RuntimeError(
            "ERROR=UNSUPPORTED_TREND_PULLBACK_SIGNATURE "
            f"required_parameter={name} "
            f"signature={signature}"
        )

    return fn(**kwargs)


def build_canonical_trades(
    bars: list[MarketBar],
    parameters: dict,
    start_index: int,
    stop_index: int,
) -> list[GrossTrade]:
    signal_fn = getattr(
        canonical_adapter,
        "trend_pullback_signal",
        None,
    )

    if signal_fn is None:
        raise RuntimeError(
            "ERROR=CANONICAL_TREND_PULLBACK_SIGNAL_MISSING"
        )

    hold_bars = int(
        parameters["hold_bars"]
    )

    # Performance-only precomputation.
    # Эти данные неизменны в пределах одного variant-run.
    signature = inspect.signature(signal_fn)
    closes = [bar.close for bar in bars]
    highs = [bar.high for bar in bars]
    lows = [bar.low for bar in bars]
    opens = [bar.open for bar in bars]

    trades: list[GrossTrade] = []

    minimum_index = max(
        int(parameters["fast_ma_period"]),
        int(parameters["slow_ma_period"]),
        start_index,
    )

    last_entry_index = (
        stop_index
        - hold_bars
        - 1
    )

    for index in range(
        minimum_index,
        last_entry_index + 1,
    ):
        raw_signal = call_canonical_signal(
            signal_fn,
            signature,
            bars,
            index,
            parameters,
            closes,
            highs,
            lows,
            opens,
        )

        direction = normalize_signal(
            raw_signal
        )

        if direction == 0:
            continue

        exit_index = index + hold_bars

        entry_price = bars[index].close
        exit_price = bars[exit_index].close

        gross_pnl = (
            exit_price - entry_price
        ) * Decimal(direction)

        trades.append(
            GrossTrade(
                entry_ts=bars[index].ts,
                exit_ts=bars[exit_index].ts,
                direction=direction,
                entry_price=entry_price,
                exit_price=exit_price,
                gross_pnl=gross_pnl,
            )
        )

    return trades


def main() -> int:
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    signal_fn = getattr(
        canonical_adapter,
        "trend_pullback_signal",
        None,
    )

    if signal_fn is None:
        raise SystemExit(
            "ERROR=CANONICAL_TREND_PULLBACK_SIGNAL_MISSING"
        )

    signature = inspect.signature(
        signal_fn
    )

    print(
        "=== UNIVERSE TREND PULLBACK "
        "CANONICAL ADAPTER SCREEN V1 ==="
    )
    print(
        "mode=canonical_true_gross_signal_screen"
    )
    print(
        f"strategy_code={STRATEGY_CODE}"
    )
    print(
        "canonical_component="
        "postgresql_edge_backtest_adapter_v1"
    )
    print(
        "canonical_signal_function="
        "trend_pullback_signal"
    )
    print(
        f"canonical_signal_signature={signature}"
    )
    print(
        "generic_execution_runner_used=0"
    )
    print(
        "signal_metric_source=GROSS_PNL"
    )
    print(
        "execution_costs_used=0"
    )
    print(
        "parameter_search_performed=0"
    )
    print()

    symbols = list(
        cfg["symbols"]
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    try:
        all_results = []
        candidates = []

        with conn.cursor(
            cursor_factory=(
                psycopg2.extras.RealDictCursor
            )
        ) as cur:
            for symbol in symbols:
                cur.execute(
                    """
                    SELECT
                        ts,
                        open,
                        high,
                        low,
                        close,
                        COALESCE(volume,0) AS volume
                    FROM public.market_bars
                    WHERE symbol=%s
                      AND timeframe=%s
                      AND open IS NOT NULL
                      AND high IS NOT NULL
                      AND low IS NOT NULL
                      AND close IS NOT NULL
                    ORDER BY ts
                    """,
                    (
                        symbol,
                        cfg["timeframe"],
                    ),
                )

                bars = [
                    MarketBar(
                        ts=row["ts"],
                        open=Decimal(str(row["open"])),
                        high=Decimal(str(row["high"])),
                        low=Decimal(str(row["low"])),
                        close=Decimal(str(row["close"])),
                        volume=Decimal(
                            str(row["volume"] or 0)
                        ),
                    )
                    for row in cur.fetchall()
                ]

                print(
                    "SYMBOL_ROW "
                    f"symbol={symbol} "
                    f"bars={len(bars)}"
                )

                if len(bars) < int(
                    cfg["minimum_bars"]
                ):
                    print(
                        "SYMBOL_SKIP "
                        f"symbol={symbol} "
                        "reason=INSUFFICIENT_BARS"
                    )
                    continue

                development_end = int(
                    len(bars)
                    * float(
                        cfg[
                            "development_fraction"
                        ]
                    )
                )

                canonical_parameter_sets = [
                    dict(
                        cfg["canonical_parameters"]
                    )
                ]

                for variant_no, parameters in enumerate(
                    canonical_parameter_sets,
                    start=1,
                ):
                    parameters = dict(parameters)

                    hold_bars = int(
                        cfg[
                            "screen_exit_horizon"
                        ]["hold_bars"]
                    )

                    # Canonical parameter contract определяется
                    # непосредственно реализацией trend_pullback_signal.
                    source = inspect.getsource(
                        signal_fn
                    )

                    import ast

                    tree = ast.parse(source)

                    required = set()

                    for node in ast.walk(tree):
                        if not isinstance(
                            node,
                            ast.Subscript,
                        ):
                            continue

                        if not (
                            isinstance(
                                node.value,
                                ast.Name,
                            )
                            and node.value.id
                            == "parameters"
                        ):
                            continue

                        if isinstance(
                            node.slice,
                            ast.Constant,
                        ):
                            key = node.slice.value

                            if isinstance(
                                key,
                                str,
                            ):
                                required.add(key)

                    missing = (
                        required
                        - set(parameters)
                    )

                    if missing:
                        raise RuntimeError(
                            "ERROR=MISSING_CANONICAL_"
                            "TREND_PULLBACK_PARAMETERS "
                            f"variant={variant_no} "
                            f"required={sorted(required)} "
                            f"provided={sorted(parameters)} "
                            f"missing={sorted(missing)}"
                        )

                    trade_parameters = dict(
                        parameters
                    )
                    trade_parameters[
                        "hold_bars"
                    ] = hold_bars

                    trades = build_canonical_trades(
                        bars,
                        trade_parameters,
                        development_end,
                        len(bars),
                    )

                    metric = gross_metrics(
                        trades
                    )

                    trade_count = int(
                        metric["trades"]
                    )

                    pf = dec(
                        metric[
                            "profit_factor"
                        ]
                    )

                    expectancy = dec(
                        metric[
                            "expectancy"
                        ]
                    )

                    candidate = (
                        trade_count
                        >= int(
                            cfg[
                                "minimum_oos_trades"
                            ]
                        )
                        and pf
                        >= dec(
                            cfg[
                                "minimum_oos_profit_factor"
                            ]
                        )
                        and expectancy
                        > dec(
                            cfg[
                                "minimum_oos_expectancy"
                            ]
                        )
                    )

                    row = {
                        "symbol": symbol,
                        "variant": variant_no,
                        "trades": trade_count,
                        "pf": pf,
                        "expectancy": expectancy,
                        "gross_pnl": dec(
                            metric[
                                "gross_pnl"
                            ]
                        ),
                        "candidate": candidate,
                    }

                    all_results.append(
                        row
                    )

                    if candidate:
                        candidates.append(
                            row
                        )

                    print(
                        "SCREEN_ROW "
                        f"symbol={symbol} "
                        f"variant={variant_no} "
                        f"fast_ma_period="
                        f"{parameters['fast_ma_period']} "
                        f"slow_ma_period="
                        f"{parameters['slow_ma_period']} "
                        "pullback_atr_multiplier="
                        f"{parameters['pullback_atr_multiplier']} "
                        f"hold_bars="
                        f"{hold_bars} "
                        f"oos_trades="
                        f"{trade_count} "
                        "gross_oos_profit_factor="
                        f"{pf} "
                        "gross_oos_expectancy="
                        f"{expectancy} "
                        "gross_oos_pnl="
                        f"{row['gross_pnl']} "
                        "signal_candidate="
                        f"{int(candidate)}"
                    )

        print()
        print("CANDIDATE_ROWS")

        ranked = sorted(
            candidates,
            key=lambda row: (
                row["expectancy"],
                row["pf"],
                row["trades"],
            ),
            reverse=True,
        )

        for rank, row in enumerate(
            ranked,
            start=1,
        ):
            print(
                "CANDIDATE_ROW "
                f"rank={rank} "
                f"symbol={row['symbol']} "
                f"strategy={STRATEGY_CODE} "
                f"variant={row['variant']} "
                f"oos_trades="
                f"{row['trades']} "
                "gross_oos_profit_factor="
                f"{row['pf']} "
                "gross_oos_expectancy="
                f"{row['expectancy']} "
                "gross_oos_pnl="
                f"{row['gross_pnl']}"
            )

        print()
        print(
            "SUMMARY_ROW "
            f"symbols={len(symbols)} "
            f"trials={len(all_results)} "
            f"signal_candidates="
            f"{len(candidates)}"
        )

        print(
            "canonical_adapter_used=1"
        )
        print(
            "generic_execution_runner_used=0"
        )
        print(
            "signal_metric_source=GROSS_PNL"
        )
        print(
            "parameter_search_performed=0"
        )
        print(
            "economic_edge_claimed=0"
        )
        print(
            "execution_costs_used=0"
        )
        print(
            "db_writes_performed=0"
        )
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")

        if candidates:
            verdict = (
                "UNIVERSE_TREND_PULLBACK_"
                "CANONICAL_CANDIDATES_FOUND"
            )
        else:
            verdict = (
                "UNIVERSE_TREND_PULLBACK_"
                "CANONICAL_NO_CANDIDATES"
            )

        print(
            f"VERDICT={verdict}"
        )

        conn.rollback()
        return 0

    finally:
        conn.close()


if __name__ == "__main__":
    raise SystemExit(main())
