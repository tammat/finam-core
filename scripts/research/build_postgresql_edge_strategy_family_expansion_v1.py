#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import importlib.util
import itertools
import pathlib
import sys
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


ROOT = pathlib.Path("/opt/finam-core")
BASE_BUILDER_PATH = (
    ROOT
    / "scripts/research/"
    "build_postgresql_edge_parameter_search_v1.py"
)

OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_edge_strategy_family_expansion_v1"
)

SOURCE_VERSION = "POSTGRESQL_EDGE_STRATEGY_FAMILY_EXPANSION_V1"


@dataclass(frozen=True, slots=True)
class ExpansionTask:
    strategy_code: str
    symbol: str
    timeframe: str
    parameter_hash: str
    parameters: dict[str, Any]


def load_base_builder() -> Any:
    specification = importlib.util.spec_from_file_location(
        "postgresql_edge_parameter_search_v1_base",
        BASE_BUILDER_PATH,
    )

    if specification is None or specification.loader is None:
        raise RuntimeError("base_builder_import_spec_missing")

    module = importlib.util.module_from_spec(specification)

    # dataclass в Python 3.13 ожидает, что модуль уже
    # зарегистрирован в sys.modules во время выполнения.
    sys.modules[specification.name] = module

    try:
        specification.loader.exec_module(module)
    except Exception:
        sys.modules.pop(specification.name, None)
        raise

    return module


def parse_csv(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def common_parameters(
    commission_per_side: Decimal,
    slippage_bps: Decimal,
    bar_limit: int,
) -> dict[str, Any]:
    return {
        "commission_per_side": float(commission_per_side),
        "slippage_bps": float(slippage_bps),
        "quantity": 1,
        "minimum_bars": 100,
        "bar_schema": "public",
        "bar_table": "market_bars",
        "bar_limit": bar_limit,
        "market_regime": "STRATEGY_FAMILY_EXPANSION_V1",
        "atr_period": 14,
        "momentum_period": 10,
        "impulse_atr_multiplier": 1.0,
    }


def mean_reversion_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        lookback,
        threshold,
        hold_bars,
        allow_short,
    ) in itertools.product(
        (20, 40),
        (1.5, 2.0),
        (3, 5),
        (False, True),
    ):
        yield {
            **base,
            "zscore_lookback": lookback,
            "zscore_entry_threshold": threshold,
            "hold_bars": hold_bars,
            "allow_short": allow_short,
            "fast_ma_period": 10,
            "slow_ma_period": 50,
            "pullback_atr_multiplier": 0.75,
            "breakout_lookback": 20,
            "minimum_atr_fraction": 0.002,
        }


def trend_pullback_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        fast_period,
        pullback_multiplier,
        hold_bars,
        allow_short,
    ) in itertools.product(
        (10, 20),
        (0.5, 1.0),
        (3, 5),
        (False, True),
    ):
        yield {
            **base,
            "fast_ma_period": fast_period,
            "slow_ma_period": 50,
            "pullback_atr_multiplier": pullback_multiplier,
            "hold_bars": hold_bars,
            "allow_short": allow_short,
            "zscore_lookback": 20,
            "zscore_entry_threshold": 2.0,
            "breakout_lookback": 20,
            "minimum_atr_fraction": 0.002,
        }


def volatility_breakout_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        breakout_lookback,
        minimum_atr_fraction,
        hold_bars,
        allow_short,
    ) in itertools.product(
        (20, 40),
        (0.002, 0.005),
        (3, 5),
        (False, True),
    ):
        yield {
            **base,
            "breakout_lookback": breakout_lookback,
            "minimum_atr_fraction": minimum_atr_fraction,
            "hold_bars": hold_bars,
            "allow_short": allow_short,
            "zscore_lookback": 20,
            "zscore_entry_threshold": 2.0,
            "fast_ma_period": 10,
            "slow_ma_period": 50,
            "pullback_atr_multiplier": 0.75,
        }


def build_tasks(
    base_builder: Any,
    *,
    symbols: list[str],
    timeframes: list[str],
    commission_per_side: Decimal,
    slippage_bps: Decimal,
    bar_limit: int,
) -> list[ExpansionTask]:
    base = common_parameters(
        commission_per_side,
        slippage_bps,
        bar_limit,
    )

    strategy_grids = (
        (
            "MEAN_REVERSION_ZSCORE_V1",
            mean_reversion_grid,
        ),
        (
            "TREND_PULLBACK_V1",
            trend_pullback_grid,
        ),
        (
            "VOLATILITY_BREAKOUT_FILTERED_V1",
            volatility_breakout_grid,
        ),
    )

    tasks: list[ExpansionTask] = []

    for symbol, timeframe in itertools.product(
        symbols,
        timeframes,
    ):
        for strategy_code, grid_builder in strategy_grids:
            for parameters in grid_builder(base):
                tasks.append(
                    ExpansionTask(
                        strategy_code=strategy_code,
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=base_builder.parameter_hash(
                            strategy_code,
                            parameters,
                        ),
                        parameters=parameters,
                    )
                )

    return tasks


def write_tsv(
    path: pathlib.Path,
    fields: tuple[str, ...],
    rows: list[dict[str, Any]],
) -> None:
    with path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fields,
            delimiter="\t",
            lineterminator="\n",
            extrasaction="ignore",
        )
        writer.writeheader()
        writer.writerows(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "PostgreSQL Edge Strategy Family Expansion V1"
        )
    )
    parser.add_argument(
        "--symbols",
        default="LKOH@MISX,SBER@MISX",
    )
    parser.add_argument(
        "--timeframes",
        default="M5",
    )
    parser.add_argument(
        "--commission-per-side",
        type=Decimal,
        default=Decimal("1.5"),
    )
    parser.add_argument(
        "--slippage-bps",
        type=Decimal,
        default=Decimal("2.0"),
    )
    parser.add_argument(
        "--bar-limit",
        type=int,
        default=20000,
    )
    parser.add_argument(
        "--batch-id",
        default=None,
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=500,
    )
    parser.add_argument(
        "--plan-only",
        action="store_true",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    base_builder = load_base_builder()

    symbols = parse_csv(args.symbols)
    timeframes = parse_csv(args.timeframes)

    if not symbols:
        raise SystemExit("ERROR=symbols_empty")

    if not timeframes:
        raise SystemExit("ERROR=timeframes_empty")

    batch_id = (
        args.batch_id
        or (
            "PG_EDGE_FAMILY_EXPANSION_V1_"
            + uuid.uuid4().hex[:12].upper()
        )
    )

    tasks = build_tasks(
        base_builder,
        symbols=symbols,
        timeframes=timeframes,
        commission_per_side=args.commission_per_side,
        slippage_bps=args.slippage_bps,
        bar_limit=args.bar_limit,
    )

    if len(tasks) > args.max_tasks:
        raise SystemExit(
            "ERROR=task_limit_exceeded:"
            f"{len(tasks)}:{args.max_tasks}"
        )

    output_dir = OUTPUT_ROOT / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_rows = [
        {
            "task_no": task_no,
            "batch_id": batch_id,
            "strategy_code": task.strategy_code,
            "symbol": task.symbol,
            "timeframe": task.timeframe,
            "parameter_hash": task.parameter_hash,
            "parameter_json": base_builder.canonical_json(
                task.parameters
            ),
        }
        for task_no, task in enumerate(tasks, start=1)
    ]

    write_tsv(
        output_dir / "search_plan.tsv",
        (
            "task_no",
            "batch_id",
            "strategy_code",
            "symbol",
            "timeframe",
            "parameter_hash",
            "parameter_json",
        ),
        plan_rows,
    )

    inserted = 0
    duplicates = 0

    if not args.plan_only:
        with psycopg2.connect(build_psycopg_url()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                inserted, duplicates = base_builder.insert_tasks(
                    cursor,
                    tasks=tasks,
                    batch_id=batch_id,
                )
            conn.commit()

    counts = {
        strategy_code: sum(
            task.strategy_code == strategy_code
            for task in tasks
        )
        for strategy_code in (
            "MEAN_REVERSION_ZSCORE_V1",
            "TREND_PULLBACK_V1",
            "VOLATILITY_BREAKOUT_FILTERED_V1",
        )
    }

    contract = (
        "POSTGRESQL EDGE STRATEGY FAMILY EXPANSION V1",
        "============================================",
        "",
        f"BATCH_ID={batch_id}",
        f"SYMBOL_COUNT={len(symbols)}",
        f"TIMEFRAME_COUNT={len(timeframes)}",
        f"TASK_COUNT={len(tasks)}",
        (
            "MEAN_REVERSION_TASK_COUNT="
            f"{counts['MEAN_REVERSION_ZSCORE_V1']}"
        ),
        (
            "TREND_PULLBACK_TASK_COUNT="
            f"{counts['TREND_PULLBACK_V1']}"
        ),
        (
            "VOLATILITY_BREAKOUT_TASK_COUNT="
            f"{counts['VOLATILITY_BREAKOUT_FILTERED_V1']}"
        ),
        f"INSERTED_COUNT={inserted}",
        f"DUPLICATE_COUNT={duplicates}",
        f"PLAN_ONLY={int(args.plan_only)}",
        f"COMMISSION_PER_SIDE={args.commission_per_side}",
        f"SLIPPAGE_BPS={args.slippage_bps}",
        f"BAR_LIMIT={args.bar_limit}",
        "DATABASE=POSTGRESQL_ONLY",
        "OOS_ALLOWED=0",
        "SHADOW_ALLOWED=0",
        "PAPER_ALLOWED=0",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "MICRO_LIVE_ALLOWED=0",
    )

    (output_dir / "contract.txt").write_text(
        "\n".join(contract) + "\n",
        encoding="utf-8",
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        [],
    )

    print(
        "=== POSTGRESQL EDGE STRATEGY "
        "FAMILY EXPANSION V1 ==="
    )
    print(f"batch_id={batch_id}")
    print(f"task_count={len(tasks)}")
    print(
        "mean_reversion_task_count="
        f"{counts['MEAN_REVERSION_ZSCORE_V1']}"
    )
    print(
        "trend_pullback_task_count="
        f"{counts['TREND_PULLBACK_V1']}"
    )
    print(
        "volatility_breakout_task_count="
        f"{counts['VOLATILITY_BREAKOUT_FILTERED_V1']}"
    )
    print(f"inserted_count={inserted}")
    print(f"duplicate_count={duplicates}")
    print(f"plan_only={int(args.plan_only)}")
    print(f"output_dir={output_dir}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "POSTGRESQL_EDGE_STRATEGY_FAMILY_EXPANSION_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
