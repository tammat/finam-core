#!/usr/bin/env python3
from __future__ import annotations

import os
import inspect
from typing import Any

import psycopg2
import psycopg2.extras

from finam_core.strategy.strategy_factory import StrategyFactory


# Русский комментарий:
# EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN — read-only проверка будущего resolver.
# Скрипт не меняет paper_pipeline.py, БД, runtime, systemd и execution.
# Цель — доказать, что equity symbol может брать strategy из runtime_active_universe
# и создавать корректный strategy instance через StrategyFactory.
# EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_ADAPTIVE_FACTORY_CALL


RUNTIME_SQL = """
SELECT
    symbol,
    strategy,
    timeframe,
    score,
    priority,
    is_enabled,
    disable_reason,
    source,
    updated_at
FROM runtime_active_universe
WHERE symbol = %s
ORDER BY is_enabled DESC, priority DESC NULLS LAST, updated_at DESC NULLS LAST
LIMIT 1;
"""


def norm(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def class_name(obj: Any) -> str:
    return obj.__class__.__name__


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise SystemExit("DATABASE_URL is required")

    symbol = os.getenv("EQUITY_WIRING_DRY_RUN_SYMBOL", "SBER@MISX")

    print("=== EQUITY STRATEGY WIRING PATCH V1 DRY RUN ===")
    print("mode=read_only")
    print("runtime_allow=0")
    print("execution_enabled=0")
    print("real_trading_enabled=0")
    print("db_update=0")
    print("file_update=0")
    print(f"symbol={symbol}")
    print()

    with psycopg2.connect(dsn) as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(RUNTIME_SQL, (symbol,))
            row = cur.fetchone()

    if not row:
        print("EQUITY_WIRING_DRY_RUN_RUNTIME_ROW found=0")
        print("EQUITY_WIRING_DRY_RUN_SUMMARY")
        print(f"symbol={symbol}")
        print("runtime_found=0")
        print("runtime_enabled=0")
        print("resolved_strategy=NONE")
        print("strategy_instance_class=NONE")
        print("factory_create_ok=0")
        print("db_update=0")
        print("file_update=0")
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_NO_RUNTIME_ROW")
        print("EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_OK")
        return 0

    runtime_strategy = norm(row.get("strategy")) or "MEAN_REVERSION_EQUITY"
    runtime_enabled = bool(row.get("is_enabled"))

    print(
        "EQUITY_WIRING_DRY_RUN_RUNTIME_ROW "
        f"symbol={norm(row.get('symbol'))} "
        f"strategy={runtime_strategy} "
        f"timeframe={norm(row.get('timeframe')) or 'UNKNOWN'} "
        f"score={row.get('score')} "
        f"priority={row.get('priority')} "
        f"is_enabled={runtime_enabled} "
        f"disable_reason={norm(row.get('disable_reason')) or 'NONE'} "
        f"source={norm(row.get('source')) or 'UNKNOWN'} "
        f"updated_at={row.get('updated_at')}"
    )

    factory_create_ok = 0
    strategy_class = "NONE"
    strategy_name = "NONE"
    error = "NONE"
    factory_call_variant = "NONE"

    factory_signature = str(inspect.signature(StrategyFactory.create))

    # Русский комментарий:
    # В проекте StrategyFactory.create мог эволюционировать.
    # Поэтому dry-run проверяет несколько безопасных вариантов вызова
    # и принимает тот, который реально резолвит VOLATILITY_BREAKOUT_EQUITY
    # в VolatilityBreakoutEquity.
    call_attempts = [
        ("keyword_strategy_name", lambda: StrategyFactory.create(strategy_name=runtime_strategy)),
        ("keyword_symbol_strategy_name", lambda: StrategyFactory.create(symbol=symbol, strategy_name=runtime_strategy)),
        ("keyword_symbol_strategy", lambda: StrategyFactory.create(symbol=symbol, strategy=runtime_strategy)),
        ("positional_strategy_name", lambda: StrategyFactory.create(runtime_strategy)),
        ("positional_symbol_strategy", lambda: StrategyFactory.create(symbol, runtime_strategy)),
    ]

    attempt_rows: list[tuple[str, int, str, str, str]] = []

    for variant, fn in call_attempts:
        try:
            obj = fn()
            cls = class_name(obj)
            name = norm(getattr(obj, "name", "")) or cls
            attempt_rows.append((variant, 1, cls, name, "NONE"))

            # Русский комментарий:
            # Если получили целевой класс, фиксируем его как правильный resolver.
            if runtime_strategy == "VOLATILITY_BREAKOUT_EQUITY" and cls == "VolatilityBreakoutEquity":
                factory_create_ok = 1
                strategy_class = cls
                strategy_name = name
                factory_call_variant = variant
                error = "NONE"
                break

            # Если целевой класс не найден, но это первый успешный вызов,
            # сохраняем его для диагностики fallback.
            if factory_create_ok == 0:
                factory_create_ok = 1
                strategy_class = cls
                strategy_name = name
                factory_call_variant = variant
                error = "NONE"

        except Exception as exc:
            attempt_rows.append((variant, 0, "NONE", "NONE", f"{type(exc).__name__}:{str(exc)}"))

    print()
    print("EQUITY_WIRING_DRY_RUN_FACTORY_SIGNATURE")
    print(f"factory_signature={factory_signature}")

    print()
    print("EQUITY_WIRING_DRY_RUN_FACTORY_ATTEMPTS")
    for variant, ok, cls, name, err in attempt_rows:
        print(
            "EQUITY_WIRING_DRY_RUN_FACTORY_ATTEMPT "
            f"variant={variant} "
            f"ok={ok} "
            f"strategy_instance_class={cls} "
            f"strategy_instance_name={name} "
            f"error={err}"
        )

    print()
    print("EQUITY_WIRING_DRY_RUN_FACTORY")
    print(f"requested_strategy={runtime_strategy}")
    print(f"factory_create_ok={factory_create_ok}")
    print(f"factory_call_variant={factory_call_variant}")
    print(f"strategy_instance_class={strategy_class}")
    print(f"strategy_instance_name={strategy_name}")
    print(f"factory_error={error}")

    expected_volatility = runtime_strategy == "VOLATILITY_BREAKOUT_EQUITY"
    resolved_to_volatility = strategy_class == "VolatilityBreakoutEquity"

    print()
    print("EQUITY_WIRING_DRY_RUN_SUMMARY")
    print(f"symbol={symbol}")
    print("runtime_found=1")
    print(f"runtime_enabled={1 if runtime_enabled else 0}")
    print(f"resolved_strategy={runtime_strategy}")
    print(f"strategy_instance_class={strategy_class}")
    print(f"strategy_instance_name={strategy_name}")
    print(f"factory_create_ok={factory_create_ok}")
    print(f"factory_call_variant={factory_call_variant}")
    print(f"expected_volatility={1 if expected_volatility else 0}")
    print(f"resolved_to_volatility={1 if resolved_to_volatility else 0}")
    print("runtime_changes_required=0")
    print("execution_changes_required=0")
    print("db_update=0")
    print("file_update=0")

    if runtime_enabled and expected_volatility and resolved_to_volatility:
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_READY")
    elif runtime_enabled and factory_create_ok:
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_FACTORY_OK_NON_VOLATILITY")
    else:
        print("VERDICT=EQUITY_STRATEGY_WIRING_PATCH_DRY_RUN_BLOCKED")

    print("EQUITY_STRATEGY_WIRING_PATCH_V1_DRY_RUN_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
