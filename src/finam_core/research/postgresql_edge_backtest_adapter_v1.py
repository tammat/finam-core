from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import statistics
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Callable, Iterable, Mapping, Sequence

import psycopg2
from psycopg2 import sql
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.finam_commission_model_v1 import (
    calculate_round_trip_commission,
    normalize_commission_parameters,
)



SOURCE_VERSION = "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
RUNNER_VERSION = "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"
SCORE_FORMULA_VERSION = "EDGE_RESEARCH_METRICS_V1"

SUPPORTED_STRATEGIES = {
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
    "MEAN_REVERSION_ZSCORE_V1",
    "TREND_PULLBACK_V1",
    "VOLATILITY_BREAKOUT_FILTERED_V1",
}

TIMESTAMP_CANDIDATES = (
    "ts",
    "bar_ts",
    "timestamp",
    "open_time",
    "time",
)

SYMBOL_CANDIDATES = (
    "symbol",
    "symbol_code",
)

TIMEFRAME_CANDIDATES = (
    "timeframe",
    "interval",
    "bar_interval",
)

DEFAULT_BAR_SCHEMA = "public"
DEFAULT_BAR_TABLE = "market_bars"


@dataclass(frozen=True, slots=True)
class Bar:
    ts: datetime
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True, slots=True)
class ResearchTask:
    id: int
    run_uuid: uuid.UUID
    research_batch_id: str
    research_code: str
    strategy_code: str
    strategy_version: str
    symbol: str
    timeframe: str
    parameter_hash: str
    parameter_json: dict[str, Any]
    dataset_version: str
    runner_version: str
    source_version: str


@dataclass(frozen=True, slots=True)
class Trade:
    trade_no: int
    side: str
    entry_ts: datetime
    exit_ts: datetime
    market_entry_price: Decimal
    market_exit_price: Decimal
    entry_price: Decimal
    exit_price: Decimal
    gross_pnl: Decimal
    commission: Decimal
    slippage: Decimal
    net_pnl: Decimal


@dataclass(frozen=True, slots=True)
class Metrics:
    bars_used: int
    trades: int
    wins: int
    losses: int
    win_rate: Decimal
    profit_factor: Decimal
    expectancy: Decimal
    avg_win: Decimal
    avg_loss: Decimal
    max_drawdown: Decimal
    recovery_factor: Decimal
    sharpe: Decimal
    sortino: Decimal
    ulcer_index: Decimal
    commission: Decimal
    slippage: Decimal
    stability_score: Decimal
    confidence_score: Decimal
    verdict_code: str


class AdapterContractError(RuntimeError):
    """Нарушение обязательного исследовательского контракта."""


def to_decimal(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def clamp_decimal(
    value: Decimal,
    lower: Decimal,
    upper: Decimal,
) -> Decimal:
    return max(lower, min(upper, value))


def first_existing(
    available: set[str],
    candidates: Sequence[str],
) -> str | None:
    for candidate in candidates:
        if candidate in available:
            return candidate
    return None


def validate_parameters(
    strategy_code: str,
    parameters: Mapping[str, Any],
) -> dict[str, Any]:
    if strategy_code not in SUPPORTED_STRATEGIES:
        raise AdapterContractError(
            f"unsupported_strategy:{strategy_code}"
        )

    required = (
        "commission_per_side",
        "slippage_bps",
    )

    missing = [
        field
        for field in required
        if field not in parameters
    ]

    if missing:
        raise AdapterContractError(
            "required_cost_parameters_missing:"
            + ",".join(missing)
        )

    commission_per_side = to_decimal(
        parameters["commission_per_side"]
    )
    slippage_bps = to_decimal(parameters["slippage_bps"])

    if commission_per_side < 0:
        raise AdapterContractError(
            "commission_per_side_must_be_non_negative"
        )

    if slippage_bps < 0:
        raise AdapterContractError(
            "slippage_bps_must_be_non_negative"
        )

    normalized = dict(parameters)
    normalized.setdefault("quantity", 1)
    normalized.setdefault("atr_period", 14)
    normalized.setdefault("impulse_atr_multiplier", 1.0)
    normalized.setdefault("momentum_period", 10)
    normalized.setdefault("hold_bars", 5)
    normalized.setdefault("minimum_bars", 100)
    normalized.setdefault("allow_short", True)

    # MEAN_REVERSION_ZSCORE_V1
    normalized.setdefault("zscore_lookback", 20)
    normalized.setdefault("zscore_entry_threshold", 2.0)

    # TREND_PULLBACK_V1
    normalized.setdefault("fast_ma_period", 10)
    normalized.setdefault("slow_ma_period", 50)
    normalized.setdefault("pullback_atr_multiplier", 0.75)

    # VOLATILITY_BREAKOUT_FILTERED_V1
    normalized.setdefault("breakout_lookback", 20)
    normalized.setdefault("minimum_atr_fraction", 0.002)

    if int(normalized["quantity"]) <= 0:
        raise AdapterContractError(
            "quantity_must_be_positive"
        )

    if int(normalized["hold_bars"]) <= 0:
        raise AdapterContractError(
            "hold_bars_must_be_positive"
        )

    if int(normalized["atr_period"]) < 2:
        raise AdapterContractError(
            "atr_period_must_be_at_least_2"
        )

    if int(normalized["momentum_period"]) < 1:
        raise AdapterContractError(
            "momentum_period_must_be_positive"
        )

    if int(normalized["zscore_lookback"]) < 5:
        raise AdapterContractError(
            "zscore_lookback_must_be_at_least_5"
        )

    if to_decimal(
        normalized["zscore_entry_threshold"]
    ) <= 0:
        raise AdapterContractError(
            "zscore_entry_threshold_must_be_positive"
        )

    if int(normalized["fast_ma_period"]) < 2:
        raise AdapterContractError(
            "fast_ma_period_must_be_at_least_2"
        )

    if (
        int(normalized["slow_ma_period"])
        <= int(normalized["fast_ma_period"])
    ):
        raise AdapterContractError(
            "slow_ma_period_must_exceed_fast_ma_period"
        )

    if to_decimal(
        normalized["pullback_atr_multiplier"]
    ) <= 0:
        raise AdapterContractError(
            "pullback_atr_multiplier_must_be_positive"
        )

    if int(normalized["breakout_lookback"]) < 5:
        raise AdapterContractError(
            "breakout_lookback_must_be_at_least_5"
        )

    if to_decimal(
        normalized["minimum_atr_fraction"]
    ) < 0:
        raise AdapterContractError(
            "minimum_atr_fraction_must_be_non_negative"
        )

    normalized = normalize_commission_parameters(normalized)
    return normalized


def apply_slippage(
    market_price: Decimal,
    side: str,
    slippage_bps: Decimal,
) -> Decimal:
    factor = slippage_bps / Decimal("10000")

    if side == "BUY":
        return market_price * (Decimal("1") + factor)

    if side == "SELL":
        return market_price * (Decimal("1") - factor)

    raise AdapterContractError(f"unsupported_order_side:{side}")


def true_range(
    current: Bar,
    previous_close: Decimal,
) -> Decimal:
    return max(
        current.high - current.low,
        abs(current.high - previous_close),
        abs(current.low - previous_close),
    )


def rolling_atr(
    bars: Sequence[Bar],
    index: int,
    period: int,
) -> Decimal | None:
    if index < period:
        return None

    ranges: list[Decimal] = []

    for position in range(index - period + 1, index + 1):
        previous_close = bars[position - 1].close
        ranges.append(
            true_range(bars[position], previous_close)
        )

    return sum(ranges, Decimal("0")) / Decimal(len(ranges))


def atr_impulse_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Mapping[str, Any],
) -> str | None:
    atr_period = int(parameters["atr_period"])
    multiplier = to_decimal(
        parameters["impulse_atr_multiplier"]
    )

    atr = rolling_atr(bars, index, atr_period)

    if atr is None or atr <= 0:
        return None

    impulse = bars[index].close - bars[index - 1].close
    threshold = atr * multiplier

    if impulse >= threshold:
        return "LONG"

    if (
        bool(parameters["allow_short"])
        and impulse <= -threshold
    ):
        return "SHORT"

    return None


def momentum_continuation_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Mapping[str, Any],
) -> str | None:
    period = int(parameters["momentum_period"])

    if index < period:
        return None

    reference = bars[index - period].close
    current = bars[index].close

    if current > reference and current > bars[index - 1].close:
        return "LONG"

    if (
        bool(parameters["allow_short"])
        and current < reference
        and current < bars[index - 1].close
    ):
        return "SHORT"

    return None



def rolling_mean(
    bars: Sequence[Bar],
    index: int,
    period: int,
) -> Decimal | None:
    if period <= 0 or index < period - 1:
        return None

    values = [
        bars[position].close
        for position in range(index - period + 1, index + 1)
    ]

    return sum(values, Decimal("0")) / Decimal(period)


def rolling_mean_std(
    bars: Sequence[Bar],
    index: int,
    period: int,
) -> tuple[Decimal, Decimal] | None:
    mean = rolling_mean(bars, index, period)

    if mean is None:
        return None

    values = [
        bars[position].close
        for position in range(index - period + 1, index + 1)
    ]

    variance = sum(
        (value - mean) * (value - mean)
        for value in values
    ) / Decimal(period)

    if variance <= 0:
        return mean, Decimal("0")

    std = Decimal(str(math.sqrt(float(variance))))
    return mean, std


def mean_reversion_zscore_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Mapping[str, Any],
) -> str | None:
    lookback = int(parameters["zscore_lookback"])
    threshold = to_decimal(
        parameters["zscore_entry_threshold"]
    )

    statistics_result = rolling_mean_std(
        bars,
        index,
        lookback,
    )

    if statistics_result is None:
        return None

    mean, std = statistics_result

    if std <= 0:
        return None

    zscore = (bars[index].close - mean) / std

    if zscore <= -threshold:
        return "LONG"

    if (
        bool(parameters["allow_short"])
        and zscore >= threshold
    ):
        return "SHORT"

    return None


def trend_pullback_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Mapping[str, Any],
) -> str | None:
    fast_period = int(parameters["fast_ma_period"])
    slow_period = int(parameters["slow_ma_period"])
    atr_period = int(parameters["atr_period"])
    pullback_multiplier = to_decimal(
        parameters["pullback_atr_multiplier"]
    )

    fast_ma = rolling_mean(bars, index, fast_period)
    slow_ma = rolling_mean(bars, index, slow_period)
    atr = rolling_atr(bars, index, atr_period)

    if (
        fast_ma is None
        or slow_ma is None
        or atr is None
        or atr <= 0
    ):
        return None

    current = bars[index].close
    pullback_distance = atr * pullback_multiplier

    if (
        fast_ma > slow_ma
        and current <= fast_ma - pullback_distance
        and current > slow_ma
    ):
        return "LONG"

    if (
        bool(parameters["allow_short"])
        and fast_ma < slow_ma
        and current >= fast_ma + pullback_distance
        and current < slow_ma
    ):
        return "SHORT"

    return None


def volatility_breakout_filtered_signal(
    bars: Sequence[Bar],
    index: int,
    parameters: Mapping[str, Any],
) -> str | None:
    lookback = int(parameters["breakout_lookback"])
    atr_period = int(parameters["atr_period"])
    minimum_atr_fraction = to_decimal(
        parameters["minimum_atr_fraction"]
    )

    if index < max(lookback, atr_period):
        return None

    atr = rolling_atr(bars, index, atr_period)

    if atr is None or atr <= 0:
        return None

    current = bars[index].close

    if current <= 0:
        return None

    atr_fraction = atr / current

    if atr_fraction < minimum_atr_fraction:
        return None

    previous_high = max(
        bars[position].high
        for position in range(index - lookback, index)
    )
    previous_low = min(
        bars[position].low
        for position in range(index - lookback, index)
    )

    if current > previous_high:
        return "LONG"

    if (
        bool(parameters["allow_short"])
        and current < previous_low
    ):
        return "SHORT"

    return None


SIGNAL_BUILDERS: dict[
    str,
    Callable[
        [Sequence[Bar], int, Mapping[str, Any]],
        str | None,
    ],
] = {
    "ATR_IMPULSE_V1": atr_impulse_signal,
    "MOMENTUM_CONTINUATION_V1": (
        momentum_continuation_signal
    ),
    "MEAN_REVERSION_ZSCORE_V1": (
        mean_reversion_zscore_signal
    ),
    "TREND_PULLBACK_V1": trend_pullback_signal,
    "VOLATILITY_BREAKOUT_FILTERED_V1": (
        volatility_breakout_filtered_signal
    ),
}


def build_trades(
    bars: Sequence[Bar],
    strategy_code: str,
    parameters: Mapping[str, Any],
) -> list[Trade]:
    normalized = validate_parameters(
        strategy_code,
        parameters,
    )

    minimum_bars = int(normalized["minimum_bars"])

    if len(bars) < minimum_bars:
        raise AdapterContractError(
            f"insufficient_bars:{len(bars)}:{minimum_bars}"
        )

    quantity = Decimal(str(normalized["quantity"]))
    hold_bars = int(normalized["hold_bars"])
    commission_per_side = to_decimal(
        normalized["commission_per_side"]
    )
    slippage_bps = to_decimal(
        normalized["slippage_bps"]
    )

    signal_builder = SIGNAL_BUILDERS[strategy_code]
    trades: list[Trade] = []

    index = 1

    while index < len(bars) - hold_bars:
        signal = signal_builder(
            bars,
            index,
            normalized,
        )

        if signal is None:
            index += 1
            continue

        exit_index = index + hold_bars
        entry_bar = bars[index]
        exit_bar = bars[exit_index]

        market_entry = entry_bar.close
        market_exit = exit_bar.close

        if signal == "LONG":
            entry_price = apply_slippage(
                market_entry,
                "BUY",
                slippage_bps,
            )
            exit_price = apply_slippage(
                market_exit,
                "SELL",
                slippage_bps,
            )
            gross_pnl = (
                exit_price - entry_price
            ) * quantity
            side = "LONG"
        else:
            entry_price = apply_slippage(
                market_entry,
                "SELL",
                slippage_bps,
            )
            exit_price = apply_slippage(
                market_exit,
                "BUY",
                slippage_bps,
            )
            gross_pnl = (
                entry_price - exit_price
            ) * quantity
            side = "SHORT"

        commission_breakdown = calculate_round_trip_commission(
            entry_price=entry_price,
            exit_price=exit_price,
            quantity_units=quantity,
            parameters=parameters,
        )
        commission = commission_breakdown.round_trip_total
        market_pnl = (
            (market_exit - market_entry) * quantity
            if side == "LONG"
            else (market_entry - market_exit) * quantity
        )

        slippage_cost = max(
            Decimal("0"),
            market_pnl - gross_pnl,
        )

        net_pnl = gross_pnl - commission

        trades.append(
            Trade(
                trade_no=len(trades) + 1,
                side=side,
                entry_ts=entry_bar.ts,
                exit_ts=exit_bar.ts,
                market_entry_price=market_entry,
                market_exit_price=market_exit,
                entry_price=entry_price,
                exit_price=exit_price,
                gross_pnl=gross_pnl,
                commission=commission,
                slippage=slippage_cost,
                net_pnl=net_pnl,
            )
        )

        # Запрещаем пересекающиеся позиции.
        index = exit_index + 1

    return trades


def calculate_drawdown(
    pnl_values: Iterable[Decimal],
) -> tuple[Decimal, Decimal]:
    equity = Decimal("0")
    peak = Decimal("0")
    maximum_drawdown = Decimal("0")
    squared_drawdowns: list[Decimal] = []

    for pnl in pnl_values:
        equity += pnl
        peak = max(peak, equity)
        drawdown = peak - equity
        maximum_drawdown = max(
            maximum_drawdown,
            drawdown,
        )
        squared_drawdowns.append(drawdown * drawdown)

    ulcer_index = (
        Decimal(
            str(
                math.sqrt(
                    float(
                        sum(
                            squared_drawdowns,
                            Decimal("0"),
                        )
                        / Decimal(len(squared_drawdowns))
                    )
                )
            )
        )
        if squared_drawdowns
        else Decimal("0")
    )

    return maximum_drawdown, ulcer_index


def calculate_stability(
    pnl_values: Sequence[Decimal],
) -> Decimal:
    if len(pnl_values) < 2:
        return Decimal("0")

    cumulative: list[float] = []
    equity = Decimal("0")

    for pnl in pnl_values:
        equity += pnl
        cumulative.append(float(equity))

    x_values = list(range(len(cumulative)))
    x_mean = statistics.fmean(x_values)
    y_mean = statistics.fmean(cumulative)

    numerator = sum(
        (x - x_mean) * (y - y_mean)
        for x, y in zip(x_values, cumulative)
    )
    denominator = sum(
        (x - x_mean) ** 2
        for x in x_values
    )

    if denominator == 0:
        return Decimal("0")

    slope = numerator / denominator
    predicted = [
        y_mean + slope * (x - x_mean)
        for x in x_values
    ]

    total_variance = sum(
        (y - y_mean) ** 2
        for y in cumulative
    )
    residual_variance = sum(
        (actual - estimate) ** 2
        for actual, estimate in zip(
            cumulative,
            predicted,
        )
    )

    if total_variance <= 0:
        return Decimal("0")

    r_squared = max(
        0.0,
        min(
            1.0,
            1.0 - residual_variance / total_variance,
        ),
    )

    return Decimal(str(r_squared * 100.0))


def calculate_metrics(
    bars_used: int,
    trades: Sequence[Trade],
) -> Metrics:
    if not trades:
        return Metrics(
            bars_used=bars_used,
            trades=0,
            wins=0,
            losses=0,
            win_rate=Decimal("0"),
            profit_factor=Decimal("0"),
            expectancy=Decimal("0"),
            avg_win=Decimal("0"),
            avg_loss=Decimal("0"),
            max_drawdown=Decimal("0"),
            recovery_factor=Decimal("0"),
            sharpe=Decimal("0"),
            sortino=Decimal("0"),
            ulcer_index=Decimal("0"),
            commission=Decimal("0"),
            slippage=Decimal("0"),
            stability_score=Decimal("0"),
            confidence_score=Decimal("0"),
            verdict_code="NO_TRADES",
        )

    pnl_values = [trade.net_pnl for trade in trades]
    wins = [value for value in pnl_values if value > 0]
    losses = [value for value in pnl_values if value < 0]

    trade_count = len(pnl_values)
    net_pnl = sum(pnl_values, Decimal("0"))
    gross_gain = sum(wins, Decimal("0"))
    gross_loss = abs(sum(losses, Decimal("0")))

    profit_factor = (
        gross_gain / gross_loss
        if gross_loss > 0
        else gross_gain
    )

    expectancy = net_pnl / Decimal(trade_count)
    avg_win = (
        gross_gain / Decimal(len(wins))
        if wins
        else Decimal("0")
    )
    avg_loss = (
        abs(sum(losses, Decimal("0")))
        / Decimal(len(losses))
        if losses
        else Decimal("0")
    )

    max_drawdown, ulcer_index = calculate_drawdown(
        pnl_values
    )

    recovery_factor = (
        net_pnl / max_drawdown
        if max_drawdown > 0
        else net_pnl
    )

    float_returns = [float(value) for value in pnl_values]

    if len(float_returns) >= 2:
        mean_return = statistics.fmean(float_returns)
        stddev = statistics.stdev(float_returns)

        sharpe = (
            Decimal(
                str(
                    mean_return
                    / stddev
                    * math.sqrt(len(float_returns))
                )
            )
            if stddev > 0
            else Decimal("0")
        )

        downside = [
            value
            for value in float_returns
            if value < 0
        ]

        downside_deviation = (
            math.sqrt(
                sum(value * value for value in downside)
                / len(downside)
            )
            if downside
            else 0.0
        )

        sortino = (
            Decimal(
                str(
                    mean_return
                    / downside_deviation
                    * math.sqrt(len(float_returns))
                )
            )
            if downside_deviation > 0
            else Decimal("0")
        )
    else:
        sharpe = Decimal("0")
        sortino = Decimal("0")

    win_rate = (
        Decimal(len(wins))
        / Decimal(trade_count)
        * Decimal("100")
    )

    stability_score = calculate_stability(pnl_values)

    sample_confidence = min(
        Decimal("1"),
        Decimal(trade_count) / Decimal("100"),
    )
    economic_confidence = (
        Decimal("1")
        if expectancy > 0 and profit_factor > 1
        else Decimal("0")
    )

    confidence_score = (
        sample_confidence
        * economic_confidence
        * Decimal("100")
    )

    verdict_code = (
        "POSITIVE_AFTER_COSTS"
        if expectancy > 0 and profit_factor > 1
        else "NEGATIVE_AFTER_COSTS"
    )

    return Metrics(
        bars_used=bars_used,
        trades=trade_count,
        wins=len(wins),
        losses=len(losses),
        win_rate=win_rate,
        profit_factor=profit_factor,
        expectancy=expectancy,
        avg_win=avg_win,
        avg_loss=avg_loss,
        max_drawdown=max_drawdown,
        recovery_factor=recovery_factor,
        sharpe=sharpe,
        sortino=sortino,
        ulcer_index=ulcer_index,
        commission=sum(
            (trade.commission for trade in trades),
            Decimal("0"),
        ),
        slippage=sum(
            (trade.slippage for trade in trades),
            Decimal("0"),
        ),
        stability_score=stability_score,
        confidence_score=confidence_score,
        verdict_code=verdict_code,
    )


def discover_bar_contract(
    cursor: RealDictCursor,
    schema_name: str,
    table_name: str,
) -> dict[str, str | None]:
    cursor.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        """,
        (schema_name, table_name),
    )

    columns = {
        str(row["column_name"])
        for row in cursor.fetchall()
    }

    required_ohlc = {
        "open",
        "high",
        "low",
        "close",
    }

    missing_ohlc = sorted(required_ohlc - columns)

    if missing_ohlc:
        raise AdapterContractError(
            "market_bar_columns_missing:"
            + ",".join(missing_ohlc)
        )

    timestamp_column = first_existing(
        columns,
        TIMESTAMP_CANDIDATES,
    )
    symbol_column = first_existing(
        columns,
        SYMBOL_CANDIDATES,
    )
    timeframe_column = first_existing(
        columns,
        TIMEFRAME_CANDIDATES,
    )

    if timestamp_column is None:
        raise AdapterContractError(
            "market_bar_timestamp_column_not_found"
        )

    if symbol_column is None:
        raise AdapterContractError(
            "market_bar_symbol_column_not_found"
        )

    return {
        "timestamp": timestamp_column,
        "symbol": symbol_column,
        "timeframe": timeframe_column,
        "volume": "volume" if "volume" in columns else None,
    }


def load_bars(
    cursor: RealDictCursor,
    task: ResearchTask,
    parameters: Mapping[str, Any],
) -> list[Bar]:
    schema_name = str(
        parameters.get(
            "bar_schema",
            DEFAULT_BAR_SCHEMA,
        )
    )
    table_name = str(
        parameters.get(
            "bar_table",
            DEFAULT_BAR_TABLE,
        )
    )

    contract = discover_bar_contract(
        cursor,
        schema_name,
        table_name,
    )

    timestamp_column = str(contract["timestamp"])
    symbol_column = str(contract["symbol"])
    timeframe_column = contract["timeframe"]
    volume_column = contract["volume"]

    limit = int(parameters.get("bar_limit", 20000))

    if limit <= 0 or limit > 1_000_000:
        raise AdapterContractError(
            f"invalid_bar_limit:{limit}"
        )

    predicates = [
        sql.SQL("{} = %s").format(
            sql.Identifier(symbol_column)
        )
    ]
    values: list[Any] = [task.symbol]

    if timeframe_column is not None:
        predicates.append(
            sql.SQL("{} = %s").format(
                sql.Identifier(str(timeframe_column))
            )
        )
        values.append(task.timeframe)

    volume_expression = (
        sql.Identifier(str(volume_column))
        if volume_column is not None
        else sql.SQL("0")
    )

    query = sql.SQL(
        """
        SELECT
            {timestamp_column} AS ts,
            open,
            high,
            low,
            close,
            {volume_expression} AS volume
        FROM {schema_name}.{table_name}
        WHERE {predicates}
        ORDER BY {timestamp_column} DESC
        LIMIT %s
        """
    ).format(
        timestamp_column=sql.Identifier(timestamp_column),
        volume_expression=volume_expression,
        schema_name=sql.Identifier(schema_name),
        table_name=sql.Identifier(table_name),
        predicates=sql.SQL(" AND ").join(predicates),
    )

    values.append(limit)
    cursor.execute(query, values)

    rows = list(reversed(cursor.fetchall()))

    bars = [
        Bar(
            ts=row["ts"],
            open=to_decimal(row["open"]),
            high=to_decimal(row["high"]),
            low=to_decimal(row["low"]),
            close=to_decimal(row["close"]),
            volume=to_decimal(row["volume"]),
        )
        for row in rows
    ]

    return bars


def row_to_task(row: Mapping[str, Any]) -> ResearchTask:
    parameter_json = row["parameter_json"]

    if isinstance(parameter_json, str):
        parameter_json = json.loads(parameter_json)

    return ResearchTask(
        id=int(row["id"]),
        run_uuid=row["run_uuid"],
        research_batch_id=str(row["research_batch_id"]),
        research_code=str(row["research_code"]),
        strategy_code=str(row["strategy_code"]),
        strategy_version=str(row["strategy_version"]),
        symbol=str(row["symbol"]),
        timeframe=str(row["timeframe"]),
        parameter_hash=str(row["parameter_hash"]),
        parameter_json=dict(parameter_json or {}),
        dataset_version=str(row["dataset_version"]),
        runner_version=str(row["runner_version"]),
        source_version=str(row["source_version"]),
    )


def claim_task(
    cursor: RealDictCursor,
    run_uuid: str | None,
) -> ResearchTask | None:
    if run_uuid:
        cursor.execute(
            """
            SELECT *
            FROM analytics.edge_lab_run_v1
            WHERE run_uuid = %s
              AND status_code IN ('QUEUED', 'FAILED')
            FOR UPDATE
            """,
            (run_uuid,),
        )
    else:
        cursor.execute(
            """
            SELECT *
            FROM analytics.edge_lab_run_v1
            WHERE status_code = 'QUEUED'
            ORDER BY created_at, id
            LIMIT 1
            FOR UPDATE SKIP LOCKED
            """
        )

    row = cursor.fetchone()

    if row is None:
        return None

    task = row_to_task(row)

    cursor.execute(
        """
        UPDATE analytics.edge_lab_run_v1
        SET
            status_code = 'RUNNING',
            started_at = clock_timestamp(),
            finished_at = NULL,
            runner_version = %s,
            updated_at = clock_timestamp()
        WHERE id = %s
        """,
        (RUNNER_VERSION, task.id),
    )

    return task


def persist_trades(
    cursor: RealDictCursor,
    task: ResearchTask,
    trades: Sequence[Trade],
) -> None:
    cursor.execute(
        """
        DELETE FROM analytics.research_trade_v1
        WHERE run_uuid = %s
        """,
        (str(task.run_uuid),),
    )

    for trade in trades:
        cursor.execute(
            """
            INSERT INTO analytics.research_trade_v1 (
                run_uuid,
                research_code,
                strategy_code,
                symbol,
                timeframe,
                trade_no,
                side,
                entry_ts,
                exit_ts,
                entry_price,
                exit_price,
                gross_pnl,
                commission,
                slippage,
                net_pnl,
                source_version
            )
            VALUES (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """,
            (
                str(task.run_uuid),
                task.research_code,
                task.strategy_code,
                task.symbol,
                task.timeframe,
                trade.trade_no,
                trade.side,
                trade.entry_ts,
                trade.exit_ts,
                trade.entry_price,
                trade.exit_price,
                trade.gross_pnl,
                trade.commission,
                trade.slippage,
                trade.net_pnl,
                SOURCE_VERSION,
            ),
        )

    cursor.execute(
        """
        SELECT
            count(*)::bigint AS trade_count,
            count(DISTINCT trade_no)::bigint
                AS distinct_trade_count
        FROM analytics.research_trade_v1
        WHERE run_uuid = %s
        """,
        (str(task.run_uuid),),
    )

    verification = cursor.fetchone()

    expected = len(trades)
    actual = int(verification["trade_count"])
    distinct = int(verification["distinct_trade_count"])

    if actual != expected or distinct != expected:
        raise AdapterContractError(
            "research_trade_persistence_mismatch:"
            f"expected={expected}:actual={actual}:"
            f"distinct={distinct}"
        )


def persist_observation(
    cursor: RealDictCursor,
    task: ResearchTask,
    metrics: Metrics,
    elapsed_ms: int,
) -> None:
    cursor.execute(
        """
        DELETE FROM analytics.edge_observation_v1
        WHERE run_uuid = %s
        """,
        (str(task.run_uuid),),
    )

    raw_edge_score = (
        metrics.expectancy
        * metrics.profit_factor
        * Decimal(metrics.trades)
    )

    normalized_edge_score = clamp_decimal(
        raw_edge_score,
        Decimal("-100"),
        Decimal("100"),
    )

    cursor.execute(
        """
        INSERT INTO analytics.edge_observation_v1 (
            run_uuid,
            research_batch_id,
            research_code,
            strategy_code,
            strategy_version,
            symbol,
            timeframe,
            parameter_hash,
            parameter_json,
            dataset_version,
            market_data_version,
            runner_version,
            score_formula_version,
            market_regime,
            bars_used,
            trades,
            wins,
            losses,
            win_rate,
            profit_factor,
            expectancy,
            avg_win,
            avg_loss,
            max_drawdown,
            recovery_factor,
            sharpe,
            sortino,
            ulcer_index,
            commission,
            slippage,
            stability_score,
            raw_edge_score,
            normalized_edge_score,
            confidence_score,
            research_cost_score,
            research_cpu_ms,
            research_memory_mb,
            research_elapsed_ms,
            verdict_code,
            source_version,
            updated_at
        )
        VALUES (
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s::jsonb, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s,
            clock_timestamp()
        )
        """,
        (
            str(task.run_uuid),
            task.research_batch_id,
            task.research_code,
            task.strategy_code,
            task.strategy_version,
            task.symbol,
            task.timeframe,
            task.parameter_hash,
            json.dumps(
                task.parameter_json,
                ensure_ascii=False,
                sort_keys=True,
            ),
            task.dataset_version,
            task.dataset_version,
            RUNNER_VERSION,
            SCORE_FORMULA_VERSION,
            str(
                task.parameter_json.get(
                    "market_regime",
                    "UNKNOWN",
                )
            ),
            metrics.bars_used,
            metrics.trades,
            metrics.wins,
            metrics.losses,
            metrics.win_rate,
            metrics.profit_factor,
            metrics.expectancy,
            metrics.avg_win,
            metrics.avg_loss,
            metrics.max_drawdown,
            metrics.recovery_factor,
            metrics.sharpe,
            metrics.sortino,
            metrics.ulcer_index,
            metrics.commission,
            metrics.slippage,
            metrics.stability_score,
            raw_edge_score,
            normalized_edge_score,
            metrics.confidence_score,
            Decimal("0"),
            elapsed_ms,
            Decimal("0"),
            elapsed_ms,
            metrics.verdict_code,
            SOURCE_VERSION,
        ),
    )

    cursor.execute(
        """
        SELECT
            trades,
            commission,
            slippage,
            expectancy,
            profit_factor,
            verdict_code
        FROM analytics.edge_observation_v1
        WHERE run_uuid = %s
        """,
        (str(task.run_uuid),),
    )

    row = cursor.fetchone()

    if row is None:
        raise AdapterContractError(
            "edge_observation_persistence_missing"
        )

    if int(row["trades"]) != metrics.trades:
        raise AdapterContractError(
            "edge_observation_trade_count_mismatch"
        )


def finalize_task(
    cursor: RealDictCursor,
    task: ResearchTask,
    status_code: str,
) -> None:
    cursor.execute(
        """
        UPDATE analytics.edge_lab_run_v1
        SET
            status_code = %s,
            finished_at = clock_timestamp(),
            runner_version = %s,
            source_version = %s,
            updated_at = clock_timestamp()
        WHERE id = %s
        """,
        (
            status_code,
            RUNNER_VERSION,
            SOURCE_VERSION,
            task.id,
        ),
    )


def mark_failed(
    connection: psycopg2.extensions.connection,
    task_id: int,
) -> None:
    with connection.cursor() as cursor:
        cursor.execute(
            """
            UPDATE analytics.edge_lab_run_v1
            SET
                status_code = 'FAILED',
                finished_at = clock_timestamp(),
                runner_version = %s,
                source_version = %s,
                updated_at = clock_timestamp()
            WHERE id = %s
            """,
            (
                RUNNER_VERSION,
                SOURCE_VERSION,
                task_id,
            ),
        )
    connection.commit()


def execute_one(
    run_uuid: str | None = None,
    dry_run: bool = False,
) -> int:
    connection_url = build_psycopg_url()
    task: ResearchTask | None = None

    connection = psycopg2.connect(connection_url)

    try:
        with connection:
            with connection.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                task = claim_task(cursor, run_uuid)

                if task is None:
                    print("queued_task_found=0")
                    print(
                        "VERDICT="
                        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_NO_TASK"
                    )
                    return 0

                parameters = validate_parameters(
                    task.strategy_code,
                    task.parameter_json,
                )
                bars = load_bars(
                    cursor,
                    task,
                    parameters,
                )

                started = time.perf_counter()
                trades = build_trades(
                    bars,
                    task.strategy_code,
                    parameters,
                )
                elapsed_ms = int(
                    (time.perf_counter() - started) * 1000
                )

                metrics = calculate_metrics(
                    len(bars),
                    trades,
                )

                print(f"run_uuid={task.run_uuid}")
                print(f"strategy_code={task.strategy_code}")
                print(f"symbol={task.symbol}")
                print(f"timeframe={task.timeframe}")
                print(f"bars_used={len(bars)}")
                print(f"trades={metrics.trades}")
                print(f"expectancy={metrics.expectancy}")
                print(f"profit_factor={metrics.profit_factor}")
                print(f"commission={metrics.commission}")
                print(f"slippage={metrics.slippage}")
                print(f"verdict_code={metrics.verdict_code}")

                if dry_run:
                    connection.rollback()
                    print("db_writes_performed=0")
                    print(
                        "VERDICT="
                        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_DRY_RUN_OK"
                    )
                    return 0

                persist_trades(
                    cursor,
                    task,
                    trades,
                )
                persist_observation(
                    cursor,
                    task,
                    metrics,
                    elapsed_ms,
                )
                finalize_task(
                    cursor,
                    task,
                    "DONE",
                )

        print("db_writes_performed=1")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_READY"
        )
        return 0

    except Exception as error:
        connection.rollback()

        if task is not None and not dry_run:
            mark_failed(connection, task.id)

        print(
            f"ERROR={type(error).__name__}:{error}",
            flush=True,
        )
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_FAILED"
        )
        return 1

    finally:
        connection.close()


def synthetic_self_test() -> int:
    base = datetime(2026, 1, 1)
    bars: list[Bar] = []
    price = Decimal("100")

    for index in range(300):
        direction = Decimal("1") if index % 20 < 12 else Decimal("-1")
        price += direction * Decimal("0.8")

        bars.append(
            Bar(
                ts=base.replace(
                    minute=index % 60,
                    hour=(index // 60) % 24,
                ),
                open=price - Decimal("0.2"),
                high=price + Decimal("0.5"),
                low=price - Decimal("0.5"),
                close=price,
                volume=Decimal("1000"),
            )
        )

    parameters = {
        "commission_per_side": "0.10",
        "slippage_bps": "2",
        "quantity": 1,
        "atr_period": 14,
        "impulse_atr_multiplier": "0.5",
        "momentum_period": 5,
        "hold_bars": 4,
        "minimum_bars": 100,
        "allow_short": True,
    }

    total_trades = 0

    for strategy_code in sorted(SUPPORTED_STRATEGIES):
        trades = build_trades(
            bars,
            strategy_code,
            parameters,
        )
        metrics = calculate_metrics(
            len(bars),
            trades,
        )

        for trade in trades:
            expected_net = (
                trade.gross_pnl - trade.commission
            )
            assert trade.net_pnl == expected_net
            assert trade.slippage >= 0

        assert metrics.trades == len(trades)
        assert metrics.commission >= 0
        assert metrics.slippage >= 0

        total_trades += len(trades)

        print(
            "SELF_TEST_STRATEGY "
            f"strategy={strategy_code} "
            f"trades={len(trades)} "
            f"expectancy={metrics.expectancy} "
            f"profit_factor={metrics.profit_factor}"
        )

    assert total_trades > 0

    print(f"self_test_total_trades={total_trades}")
    print("sqlite_used=0")
    print("db_writes_performed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1_SELF_TEST_OK"
    )
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Edge Backtest Adapter V1"
        )
    )
    parser.add_argument(
        "--run-uuid",
        default=None,
        help="Запустить конкретную QUEUED/FAILED задачу",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Выполнить расчёт с rollback",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Синтетический тест без PostgreSQL",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    if args.self_test:
        return synthetic_self_test()

    return execute_one(
        run_uuid=args.run_uuid,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    raise SystemExit(main())
