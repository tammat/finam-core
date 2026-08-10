#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

export PYTHONPATH=src

echo "=== TEST_CANONICAL_ADAPTER_PERFORMANCE_REGRESSION_V1 ==="

python - <<'PY'
from __future__ import annotations

import importlib.util
import inspect
import json
import math
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from importlib.machinery import SourceFileLoader
from pathlib import Path


ROOT = Path("/opt/finam-core")

NEW_PATH = ROOT / (
    "src/scripts/research/"
    "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
)

OLD_PATH = Path(str(NEW_PATH) + ".pre_perf_fix_v1")

CONFIG_PATH = ROOT / (
    "config/research/"
    "trend_pullback_canonical_robustness_v1.json"
)


def load_module(name: str, path: Path):
    loader = SourceFileLoader(name, str(path))
    spec = importlib.util.spec_from_loader(name, loader)

    if spec is None:
        raise RuntimeError(
            f"ERROR=MODULE_SPEC_FAILED path={path}"
        )

    module = importlib.util.module_from_spec(spec)

    # Важно для dataclass / module metadata.
    sys.modules[name] = module
    loader.exec_module(module)

    return module


def recursive_dicts(value):
    if isinstance(value, dict):
        yield value

        for child in value.values():
            yield from recursive_dicts(child)

    elif isinstance(value, list):
        for child in value:
            yield from recursive_dicts(child)


def recursive_find_key(value, key):
    if isinstance(value, dict):
        if key in value:
            return value[key]

        for child in value.values():
            result = recursive_find_key(child, key)

            if result is not None:
                return result

    elif isinstance(value, list):
        for child in value:
            result = recursive_find_key(child, key)

            if result is not None:
                return result

    return None


def load_parameters():
    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    required = {
        "fast_ma_period",
        "slow_ma_period",
    }

    candidate = None

    for item in recursive_dicts(cfg):
        if required.issubset(item.keys()):
            candidate = dict(item)
            break

    if candidate is None:
        raise RuntimeError(
            "ERROR=CANONICAL_PARAMETERS_NOT_FOUND_IN_CONFIG"
        )

    candidate.pop("code", None)

    if "hold_bars" not in candidate:
        hold_bars = recursive_find_key(
            cfg,
            "hold_bars",
        )

        if hold_bars is None:
            raise RuntimeError(
                "ERROR=HOLD_BARS_NOT_FOUND_IN_CONFIG"
            )

        candidate["hold_bars"] = hold_bars

    return candidate


def make_market_bar(module, index: int):
    signature = inspect.signature(
        module.MarketBar
    )

    ts = (
        datetime(
            2026,
            1,
            1,
            tzinfo=timezone.utc,
        )
        + timedelta(minutes=5 * index)
    )

    # Детерминированный синтетический ряд:
    # trend + циклические pullbacks + небольшой breakout-компонент.
    base = (
        Decimal("100")
        + Decimal(index) * Decimal("0.015")
    )

    wave = Decimal(
        str(
            math.sin(index / 11.0) * 1.8
            + math.sin(index / 37.0) * 0.9
        )
    )

    close = base + wave

    open_price = (
        close
        - Decimal(
            str(math.sin(index / 7.0) * 0.15)
        )
    )

    high = max(open_price, close) + Decimal("0.35")
    low = min(open_price, close) - Decimal("0.35")

    values = {
        "ts": ts,
        "timestamp": ts,
        "time": ts,
        "datetime": ts,

        "open": open_price,
        "open_price": open_price,

        "high": high,
        "high_price": high,

        "low": low,
        "low_price": low,

        "close": close,
        "close_price": close,

        "volume": Decimal("1000"),
        "symbol": "REGRESSION@TEST",
        "timeframe": "M5",
    }

    kwargs = {}

    for name, parameter in signature.parameters.items():
        if name in values:
            kwargs[name] = values[name]
            continue

        if parameter.default is not inspect.Parameter.empty:
            continue

        raise RuntimeError(
            "ERROR=UNSUPPORTED_MARKET_BAR_FIELD "
            f"field={name} signature={signature}"
        )

    return module.MarketBar(**kwargs)


def trade_tuple(trade):
    return (
        trade.entry_ts,
        trade.exit_ts,
        trade.direction,
        trade.entry_price,
        trade.exit_price,
        trade.gross_pnl,
    )


old = load_module(
    "canonical_adapter_old_regression_v1",
    OLD_PATH,
)

new = load_module(
    "canonical_adapter_new_regression_v1",
    NEW_PATH,
)

parameters = load_parameters()

# Достаточно для semantic regression,
# но старую O(N²)-подобную реализацию не заставляем
# считать десятки тысяч баров.
BAR_COUNT = 1500

old_bars = [
    make_market_bar(old, i)
    for i in range(BAR_COUNT)
]

new_bars = [
    make_market_bar(new, i)
    for i in range(BAR_COUNT)
]

old_signal_fn = getattr(
    old.canonical_adapter,
    "trend_pullback_signal",
)

new_signal_fn = getattr(
    new.canonical_adapter,
    "trend_pullback_signal",
)

new_signature = inspect.signature(
    new_signal_fn
)

new_closes = [
    bar.close for bar in new_bars
]

new_highs = [
    bar.high for bar in new_bars
]

new_lows = [
    bar.low for bar in new_bars
]

new_opens = [
    bar.open for bar in new_bars
]

start_index = max(
    int(parameters["fast_ma_period"]),
    int(parameters["slow_ma_period"]),
)

stop_index = BAR_COUNT

hold_bars = int(
    parameters["hold_bars"]
)

last_entry_index = (
    stop_index
    - hold_bars
    - 1
)

signal_checked = 0
signal_diff = 0

for index in range(
    start_index,
    last_entry_index + 1,
):
    old_raw = old.call_canonical_signal(
        old_signal_fn,
        old_bars,
        index,
        parameters,
    )

    new_raw = new.call_canonical_signal(
        new_signal_fn,
        new_signature,
        new_bars,
        index,
        parameters,
        new_closes,
        new_highs,
        new_lows,
        new_opens,
    )

    old_direction = old.normalize_signal(
        old_raw
    )

    new_direction = new.normalize_signal(
        new_raw
    )

    signal_checked += 1

    if old_direction != new_direction:
        signal_diff += 1

        if signal_diff <= 10:
            print(
                "SIGNAL_DIFF "
                f"index={index} "
                f"old={old_direction} "
                f"new={new_direction}"
            )


old_trades = old.build_canonical_trades(
    old_bars,
    parameters,
    start_index,
    stop_index,
)

new_trades = new.build_canonical_trades(
    new_bars,
    parameters,
    start_index,
    stop_index,
)

old_serialized = [
    trade_tuple(trade)
    for trade in old_trades
]

new_serialized = [
    trade_tuple(trade)
    for trade in new_trades
]

trade_diff = (
    old_serialized != new_serialized
)

old_metric = old.gross_metrics(
    old_trades
)

new_metric = new.gross_metrics(
    new_trades
)

metric_keys = (
    "trades",
    "gross_pnl",
    "profit_factor",
    "expectancy",
)

metric_diff = 0

for key in metric_keys:
    old_value = old_metric[key]
    new_value = new_metric[key]

    if old_value != new_value:
        metric_diff += 1

        print(
            "METRIC_DIFF "
            f"metric={key} "
            f"old={old_value} "
            f"new={new_value}"
        )


semantic_diff = (
    signal_diff
    + int(trade_diff)
    + metric_diff
)

print(
    f"bars={BAR_COUNT}"
)

print(
    f"signals_checked={signal_checked}"
)

print(
    f"signal_diff={signal_diff}"
)

print(
    f"old_trade_count={len(old_trades)}"
)

print(
    f"new_trade_count={len(new_trades)}"
)

print(
    f"trade_diff={int(trade_diff)}"
)

print(
    f"metric_diff={metric_diff}"
)

print(
    f"semantic_diff={semantic_diff}"
)

print(
    "runtime_changed=0"
)

print(
    "execution_changed=0"
)

print(
    "orders_changed=0"
)

print(
    "fills_changed=0"
)

print(
    "micro_live_allowed=0"
)

if semantic_diff != 0:
    raise SystemExit(
        "ERROR=CANONICAL_ADAPTER_SEMANTIC_REGRESSION"
    )

print(
    "VERDICT="
    "TEST_CANONICAL_ADAPTER_PERFORMANCE_REGRESSION_V1_OK"
)
PY
