#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import hashlib
import itertools
import json
import pathlib
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Iterable

import psycopg2
from psycopg2 import sql
from psycopg2.extras import Json, RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url
from finam_core.research.postgresql_edge_backtest_adapter_v1 import (
    AdapterContractError,
    SUPPORTED_STRATEGIES,
    validate_parameters,
)
from finam_core.research.finam_commission_model_v1 import (
    MODEL_FINAM_FUTURES_CONFIGURED_V1,
)


SOURCE_VERSION = "POSTGRESQL_EDGE_PARAMETER_SEARCH_V1"
RUNNER_VERSION = "POSTGRESQL_EDGE_BACKTEST_ADAPTER_V1"

DEFAULT_OUTPUT_ROOT = pathlib.Path(
    "/tmp/postgresql_edge_parameter_search_v1"
)

DEFAULT_STRATEGIES = (
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
)

SUPPORTED_STRATEGIES = (
    "ATR_IMPULSE_V1",
    "MOMENTUM_CONTINUATION_V1",
    "MEAN_REVERSION_ZSCORE_V1",
    "TREND_PULLBACK_V1",
    "VOLATILITY_BREAKOUT_FILTERED_V1",
)


@dataclass(frozen=True, slots=True)
class SearchTask:
    strategy_code: str
    symbol: str
    timeframe: str
    parameter_hash: str
    parameters: dict[str, Any]


def parse_csv(value: str) -> list[str]:
    return [
        item.strip()
        for item in value.split(",")
        if item.strip()
    ]


def canonical_json(parameters: dict[str, Any]) -> str:
    return json.dumps(
        parameters,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def parameter_hash(
    strategy_code: str,
    parameters: dict[str, Any],
) -> str:
    # Идентичные параметры разных стратегий не являются одной задачей.
    identity = {
        "strategy_code": strategy_code,
        "parameters": parameters,
    }

    return hashlib.md5(
        canonical_json(identity).encode("utf-8")
    ).hexdigest()


def load_verified_futures_costs(
    symbols: list[str],
) -> dict[str, dict[str, Any]]:
    """
    Загружает доказанный cost contract для concrete BR/NG futures.

    Broker fee берётся из VERIFIED CONTRACT_COUNT evidence.
    Exchange fee берётся из актуального MOEX SCALPERFEE.
    Любая неоднозначность блокирует построение futures search.
    """
    futures_symbols = sorted(
        {
            symbol
            for symbol in symbols
            if symbol.endswith("@RTSX")
        }
    )

    if not futures_symbols:
        return {}

    unsupported = [
        symbol
        for symbol in futures_symbols
        if not (
            symbol.startswith("BR")
            or symbol.startswith("NG")
        )
    ]

    if unsupported:
        raise RuntimeError(
            "futures_broker_fee_evidence_unresolved:"
            + ",".join(unsupported)
        )

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    min(commission_per_contract) AS min_fee,
                    max(commission_per_contract) AS max_fee,
                    count(*)::bigint AS evidence_rows
                FROM analytics.futures_commission_allocation_v1
                WHERE evidence_status = 'VERIFIED'
                  AND allocation_model = 'CONTRACT_COUNT'
                  AND (
                       symbol LIKE 'BR%%@RTSX'
                       OR symbol LIKE 'NG%%@RTSX'
                  )
                """
            )
            broker_row = cursor.fetchone()

            if (
                broker_row is None
                or int(broker_row["evidence_rows"] or 0) == 0
            ):
                raise RuntimeError(
                    "verified_futures_broker_fee_missing"
                )

            min_fee = Decimal(
                str(broker_row["min_fee"])
            )
            max_fee = Decimal(
                str(broker_row["max_fee"])
            )

            if min_fee <= 0:
                raise RuntimeError(
                    "verified_futures_broker_fee_not_positive"
                )

            fee_tolerance = Decimal("0.000001")

            if max_fee - min_fee > fee_tolerance:
                raise RuntimeError(
                    "verified_futures_broker_fee_conflict:"
                    f"min={min_fee}:max={max_fee}"
                )

            broker_fee = min_fee

            cursor.execute(
                """
                SELECT
                    symbol,
                    scalper_fee,
                    source_version
                FROM analytics.market_contract_cost_spec_v1
                WHERE symbol = ANY(%s)
                  AND source_version =
                      'MOEX_ISS_CONTRACT_SPEC_V1'
                ORDER BY symbol
                """,
                (futures_symbols,),
            )
            exchange_rows = cursor.fetchall()

    by_symbol = {
        str(row["symbol"]): row
        for row in exchange_rows
    }

    missing = [
        symbol
        for symbol in futures_symbols
        if symbol not in by_symbol
    ]

    if missing:
        raise RuntimeError(
            "futures_exchange_fee_evidence_missing:"
            + ",".join(missing)
        )

    result: dict[str, dict[str, Any]] = {}

    for symbol in futures_symbols:
        row = by_symbol[symbol]
        exchange_fee = Decimal(
            str(row["scalper_fee"])
        )

        if exchange_fee <= 0:
            raise RuntimeError(
                "futures_exchange_fee_not_positive:"
                f"{symbol}"
            )

        result[symbol] = {
            "commission_model": (
                MODEL_FINAM_FUTURES_CONFIGURED_V1
            ),
            "commission_per_side": 0.0,
            "futures_broker_fee_per_contract_per_side": (
                float(broker_fee)
            ),
            "futures_exchange_fee_per_contract_per_side": (
                float(exchange_fee)
            ),
            "futures_other_fee_per_contract_per_side": 0.0,
            "futures_fee_evidence_verified": True,
        }

    return result


def common_parameters(
    *,
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
        "market_regime": "PARAMETER_SEARCH_V1",
    }


def build_atr_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        atr_period,
        multiplier,
        hold_bars,
        allow_short,
    ) in itertools.product(
        (10, 14),
        (0.75, 1.0, 1.5),
        (3, 5),
        (False, True),
    ):
        yield {
            **base,
            "atr_period": atr_period,
            "impulse_atr_multiplier": multiplier,
            "momentum_period": 10,
            "hold_bars": hold_bars,
            "allow_short": allow_short,
        }


def build_momentum_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        momentum_period,
        hold_bars,
        allow_short,
    ) in itertools.product(
        (5, 10, 20),
        (3, 5),
        (False, True),
    ):
        yield {
            **base,
            "atr_period": 14,
            "impulse_atr_multiplier": 1.0,
            "momentum_period": momentum_period,
            "hold_bars": hold_bars,
            "allow_short": allow_short,
        }


def build_mean_reversion_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        lookback,
        threshold,
        hold_bars,
    ) in itertools.product(
        (10, 20, 40),
        (1.5, 2.0, 2.5),
        (3, 5),
    ):
        yield {
            **base,
            "zscore_lookback": lookback,
            "zscore_entry_threshold": threshold,
            "hold_bars": hold_bars,
            "allow_short": True,
        }


def build_trend_pullback_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        fast_period,
        slow_period,
        pullback_multiplier,
        hold_bars,
    ) in itertools.product(
        (10, 20),
        (50, 100),
        (0.5, 0.75, 1.0),
        (3, 5),
    ):
        yield {
            **base,
            "atr_period": 14,
            "fast_ma_period": fast_period,
            "slow_ma_period": slow_period,
            "pullback_atr_multiplier": pullback_multiplier,
            "hold_bars": hold_bars,
            "allow_short": True,
        }


def build_volatility_breakout_grid(
    base: dict[str, Any],
) -> Iterable[dict[str, Any]]:
    for (
        lookback,
        minimum_atr_fraction,
        hold_bars,
    ) in itertools.product(
        (10, 20, 40),
        (0.001, 0.002, 0.004),
        (3, 5),
    ):
        yield {
            **base,
            "atr_period": 14,
            "breakout_lookback": lookback,
            "minimum_atr_fraction": minimum_atr_fraction,
            "hold_bars": hold_bars,
            "allow_short": True,
        }


def build_search_tasks(
    *,
    symbols: list[str],
    timeframes: list[str],
    commission_per_side: Decimal,
    slippage_bps: Decimal,
    bar_limit: int,
    strategies: tuple[str, ...] | None = None,
    futures_cost_by_symbol: (
        dict[str, dict[str, Any]] | None
    ) = None,
) -> list[SearchTask]:
    tasks: list[SearchTask] = []
    futures_cost_by_symbol = (
        futures_cost_by_symbol or {}
    )

    selected_strategies = set(
        strategies or DEFAULT_STRATEGIES
    )

    for symbol, timeframe in itertools.product(
        symbols,
        timeframes,
    ):
        base = common_parameters(
            commission_per_side=commission_per_side,
            slippage_bps=slippage_bps,
            bar_limit=bar_limit,
        )

        if symbol.endswith("@RTSX"):
            futures_cost = futures_cost_by_symbol.get(
                symbol
            )

            if futures_cost is None:
                raise RuntimeError(
                    "futures_cost_contract_missing:"
                    f"{symbol}"
                )

            base.update(futures_cost)

        if "ATR_IMPULSE_V1" in selected_strategies:
            for parameters in build_atr_grid(base):
                tasks.append(
                    SearchTask(
                        strategy_code="ATR_IMPULSE_V1",
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=parameter_hash(
                            "ATR_IMPULSE_V1",
                            parameters,
                        ),
                        parameters=parameters,
                    )
                )

        if "MOMENTUM_CONTINUATION_V1" in selected_strategies:
            for parameters in build_momentum_grid(base):
                tasks.append(
                    SearchTask(
                        strategy_code="MOMENTUM_CONTINUATION_V1",
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=parameter_hash(
                            "MOMENTUM_CONTINUATION_V1",
                            parameters,
                        ),
                        parameters=parameters,
                    )
                )

        if "MEAN_REVERSION_ZSCORE_V1" in selected_strategies:
            for parameters in build_mean_reversion_grid(base):
                tasks.append(
                    SearchTask(
                        strategy_code="MEAN_REVERSION_ZSCORE_V1",
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=parameter_hash(
                            "MEAN_REVERSION_ZSCORE_V1",
                            parameters,
                        ),
                        parameters=parameters,
                    )
                )

        if "TREND_PULLBACK_V1" in selected_strategies:
            for parameters in build_trend_pullback_grid(base):
                tasks.append(
                    SearchTask(
                        strategy_code="TREND_PULLBACK_V1",
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=parameter_hash(
                            "TREND_PULLBACK_V1",
                            parameters,
                        ),
                        parameters=parameters,
                    )
                )

        if (
            "VOLATILITY_BREAKOUT_FILTERED_V1"
            in selected_strategies
        ):
            for parameters in build_volatility_breakout_grid(base):
                tasks.append(
                    SearchTask(
                        strategy_code=(
                            "VOLATILITY_BREAKOUT_FILTERED_V1"
                        ),
                        symbol=symbol,
                        timeframe=timeframe,
                        parameter_hash=parameter_hash(
                            "VOLATILITY_BREAKOUT_FILTERED_V1",
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


def load_templates(
    cursor: RealDictCursor,
) -> dict[str, dict[str, Any]]:
    templates: dict[str, dict[str, Any]] = {}

    for strategy_code in SUPPORTED_STRATEGIES:
        cursor.execute(
            """
            SELECT *
            FROM analytics.edge_lab_run_v1
            WHERE strategy_code = %s
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            (strategy_code,),
        )
        row = cursor.fetchone()

        if row is None:
            raise RuntimeError(
                f"template_task_missing:{strategy_code}"
            )

        templates[strategy_code] = dict(row)

    return templates


def insertable_columns(
    cursor: RealDictCursor,
) -> list[str]:
    cursor.execute(
        """
        SELECT
            column_name,
            is_identity,
            is_generated
        FROM information_schema.columns
        WHERE table_schema = 'analytics'
          AND table_name = 'edge_lab_run_v1'
        ORDER BY ordinal_position
        """
    )

    excluded = {
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "finished_at",
    }

    return [
        str(row["column_name"])
        for row in cursor.fetchall()
        if row["column_name"] not in excluded
        and row["is_identity"] == "NO"
        and row["is_generated"] == "NEVER"
    ]


def insert_tasks(
    cursor: RealDictCursor,
    *,
    tasks: list[SearchTask],
    batch_id: str,
) -> tuple[int, int]:
    templates = load_templates(cursor)
    columns = insertable_columns(cursor)

    # Новые исследовательские стратегии могут ещё не иметь
    # исторических строк в edge_lab_run_v1. В таком случае
    # используем одну общую валидную строку только как структурный
    # шаблон, после чего все идентифицирующие поля переопределяются.
    missing_strategy_codes = sorted(
        {
            task.strategy_code
            for task in tasks
            if task.strategy_code not in templates
        }
    )

    if missing_strategy_codes:
        cursor.execute(
            """
            SELECT *
            FROM analytics.edge_lab_run_v1
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """
        )
        generic_template = cursor.fetchone()

        if generic_template is None:
            raise RuntimeError(
                "generic_edge_lab_task_template_missing"
            )

        for strategy_code in missing_strategy_codes:
            templates[strategy_code] = dict(generic_template)

    inserted = 0
    duplicates = 0

    query = sql.SQL(
        """
        INSERT INTO analytics.edge_lab_run_v1 ({columns})
        VALUES ({placeholders})
        RETURNING id
        """
    ).format(
        columns=sql.SQL(", ").join(
            sql.Identifier(column)
            for column in columns
        ),
        placeholders=sql.SQL(", ").join(
            sql.Placeholder()
            for _ in columns
        ),
    )

    batch_identity = hashlib.sha256(
        batch_id.encode("utf-8")
    ).hexdigest()[:10]

    for task_no, task in enumerate(tasks, start=1):
        template = dict(templates[task.strategy_code])

        research_code = (
            f"PG_SEARCH_V1:{batch_identity}:"
            f"{task.strategy_code}:"
            f"{task.symbol}:{task.timeframe}:"
            f"{task_no:04d}:{task.parameter_hash[:8]}"
        )

        cursor.execute(
            """
            SELECT 1
            FROM analytics.edge_lab_run_v1
            WHERE research_code = %s
              AND strategy_code = %s
              AND symbol = %s
              AND timeframe = %s
              AND parameter_hash = %s
              AND dataset_version = %s
            LIMIT 1
            """,
            (
                research_code,
                task.strategy_code,
                task.symbol,
                task.timeframe,
                task.parameter_hash,
                str(template["dataset_version"]),
            ),
        )

        if cursor.fetchone() is not None:
            duplicates += 1
            continue

        if task.strategy_code not in SUPPORTED_STRATEGIES:
            print(
                "PRECHECK_FAILED "
                f"reason=UNSUPPORTED_STRATEGY "
                f"strategy={task.strategy_code} "
                f"symbol={task.symbol} "
                f"timeframe={task.timeframe}"
            )
            continue

        try:
            normalized_parameters = validate_parameters(
                task.strategy_code,
                dict(task.parameters),
            )
        except AdapterContractError as error:
            print(
                "PRECHECK_FAILED "
                f"reason=INVALID_PARAMETER_CONTRACT "
                f"strategy={task.strategy_code} "
                f"symbol={task.symbol} "
                f"timeframe={task.timeframe} "
                f"error={error}"
            )
            continue

        run_uuid = str(uuid.uuid4())

        values = {
            **template,
            "run_uuid": run_uuid,
            "research_batch_id": batch_id,
            "research_code": research_code,
            "strategy_code": task.strategy_code,
            "strategy_version": "v1",
            "symbol": task.symbol,
            "timeframe": task.timeframe,
            "parameter_hash": task.parameter_hash,
            "parameter_json": Json(normalized_parameters),
            "status_code": "QUEUED",
            "runner_version": RUNNER_VERSION,
            "source_version": SOURCE_VERSION,
        }

        missing = [
            column
            for column in columns
            if column not in values
        ]

        if missing:
            raise RuntimeError(
                "template_values_missing:"
                + ",".join(missing)
            )

        minimum_bars = int(
            normalized_parameters.get("minimum_bars", 100)
        )

        cursor.execute(
            """
            SELECT count(*)::bigint AS bar_count
            FROM public.market_bars
            WHERE symbol = %s
              AND timeframe = %s
            """,
            (
                task.symbol,
                task.timeframe,
            ),
        )

        bar_count = int(
            cursor.fetchone()["bar_count"] or 0
        )

        if bar_count == 0:
            print(
                "PRECHECK_FAILED "
                f"reason=NO_BARS "
                f"strategy={task.strategy_code} "
                f"symbol={task.symbol} "
                f"timeframe={task.timeframe}"
            )
            continue

        if bar_count < minimum_bars:
            print(
                "PRECHECK_FAILED "
                f"reason=INSUFFICIENT_BARS "
                f"strategy={task.strategy_code} "
                f"symbol={task.symbol} "
                f"timeframe={task.timeframe} "
                f"bars={bar_count} "
                f"minimum_bars={minimum_bars}"
            )
            continue

        cursor.execute(
            query,
            [values[column] for column in columns],
        )
        inserted += 1

    return inserted, duplicates


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PostgreSQL Edge Parameter Search V1"
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
    parser.add_argument(
        "--strategies",
        nargs="+",
        choices=SUPPORTED_STRATEGIES,
        default=None,
        help=(
            "Ограничить генерацию указанными "
            "strategy family. По умолчанию "
            "сохраняется прежнее поведение."
        ),
    )

    return parser.parse_args()


def main() -> int:
    args = parse_args()

    symbols = parse_csv(args.symbols)
    timeframes = parse_csv(args.timeframes)

    if not symbols:
        raise SystemExit("ERROR=symbols_empty")

    if not timeframes:
        raise SystemExit("ERROR=timeframes_empty")

    if args.commission_per_side < 0:
        raise SystemExit(
            "ERROR=commission_per_side_negative"
        )

    if args.slippage_bps < 0:
        raise SystemExit("ERROR=slippage_bps_negative")

    if args.bar_limit < 100:
        raise SystemExit("ERROR=bar_limit_below_100")

    batch_id = (
        args.batch_id
        or (
            "PG_EDGE_SEARCH_V1_"
            + uuid.uuid4().hex[:12].upper()
        )
    )

    futures_cost_by_symbol = (
        load_verified_futures_costs(symbols)
    )

    tasks = build_search_tasks(
        symbols=symbols,
        timeframes=timeframes,
        commission_per_side=args.commission_per_side,
        slippage_bps=args.slippage_bps,
        bar_limit=args.bar_limit,
        futures_cost_by_symbol=(
            futures_cost_by_symbol
        ),
        strategies=(
            tuple(args.strategies)
            if args.strategies
            else None
        ),
    )

    if len(tasks) > args.max_tasks:
        raise SystemExit(
            "ERROR=task_limit_exceeded:"
            f"tasks={len(tasks)}:"
            f"max_tasks={args.max_tasks}"
        )

    output_dir = DEFAULT_OUTPUT_ROOT / batch_id
    output_dir.mkdir(parents=True, exist_ok=True)

    plan_rows = [
        {
            "task_no": index,
            "batch_id": batch_id,
            "strategy_code": task.strategy_code,
            "symbol": task.symbol,
            "timeframe": task.timeframe,
            "parameter_hash": task.parameter_hash,
            "parameter_json": canonical_json(task.parameters),
        }
        for index, task in enumerate(tasks, start=1)
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

    atr_count = sum(
        task.strategy_code == "ATR_IMPULSE_V1"
        for task in tasks
    )
    momentum_count = sum(
        task.strategy_code
        == "MOMENTUM_CONTINUATION_V1"
        for task in tasks
    )
    mean_reversion_count = sum(
        task.strategy_code
        == "MEAN_REVERSION_ZSCORE_V1"
        for task in tasks
    )
    trend_pullback_count = sum(
        task.strategy_code
        == "TREND_PULLBACK_V1"
        for task in tasks
    )
    volatility_breakout_count = sum(
        task.strategy_code
        == "VOLATILITY_BREAKOUT_FILTERED_V1"
        for task in tasks
    )

    inserted = 0
    duplicates = 0

    if not args.plan_only:
        with psycopg2.connect(build_psycopg_url()) as conn:
            with conn.cursor(
                cursor_factory=RealDictCursor,
            ) as cursor:
                inserted, duplicates = insert_tasks(
                    cursor,
                    tasks=tasks,
                    batch_id=batch_id,
                )
            conn.commit()

    contract_lines = (
        "POSTGRESQL EDGE PARAMETER SEARCH V1",
        "===================================",
        "",
        f"BATCH_ID={batch_id}",
        f"SYMBOL_COUNT={len(symbols)}",
        f"TIMEFRAME_COUNT={len(timeframes)}",
        f"TASK_COUNT={len(tasks)}",
        f"ATR_TASK_COUNT={atr_count}",
        f"MOMENTUM_TASK_COUNT={momentum_count}",
        f"MEAN_REVERSION_TASK_COUNT={mean_reversion_count}",
        f"TREND_PULLBACK_TASK_COUNT={trend_pullback_count}",
        (
            "VOLATILITY_BREAKOUT_TASK_COUNT="
            f"{volatility_breakout_count}"
        ),
        f"INSERTED_COUNT={inserted}",
        f"DUPLICATE_COUNT={duplicates}",
        f"PLAN_ONLY={int(args.plan_only)}",
        f"COMMISSION_PER_SIDE={args.commission_per_side}",
        f"SLIPPAGE_BPS={args.slippage_bps}",
        f"BAR_LIMIT={args.bar_limit}",
        "DATABASE=POSTGRESQL_ONLY",
        "RUNTIME_CHANGED=0",
        "EXECUTION_CHANGED=0",
        "ORDERS_CHANGED=0",
        "FILLS_CHANGED=0",
        "MICRO_LIVE_ALLOWED=0",
    )

    (output_dir / "contract.txt").write_text(
        "\n".join(contract_lines) + "\n",
        encoding="utf-8",
    )

    write_tsv(
        output_dir / "unresolved.tsv",
        ("scope", "identity", "reason"),
        [],
    )

    print("=== POSTGRESQL EDGE PARAMETER SEARCH V1 ===")
    print(f"batch_id={batch_id}")
    print(f"symbol_count={len(symbols)}")
    print(f"timeframe_count={len(timeframes)}")
    print(f"task_count={len(tasks)}")
    print(f"atr_task_count={atr_count}")
    print(f"momentum_task_count={momentum_count}")
    print(
        f"mean_reversion_task_count="
        f"{mean_reversion_count}"
    )
    print(
        f"trend_pullback_task_count="
        f"{trend_pullback_count}"
    )
    print(
        f"volatility_breakout_task_count="
        f"{volatility_breakout_count}"
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
        "POSTGRESQL_EDGE_PARAMETER_SEARCH_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
