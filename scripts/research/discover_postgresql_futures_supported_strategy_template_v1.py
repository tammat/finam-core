#!/usr/bin/env python3
from __future__ import annotations

import ast
import pathlib
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


ROOT = pathlib.Path("/opt/finam-core")
ADAPTER = (
    ROOT
    / "src/finam_core/research/"
    "postgresql_edge_backtest_adapter_v1.py"
)


def literal_string_collection(
    source: str,
    variable_name: str,
) -> set[str]:
    tree = ast.parse(source, filename=str(ADAPTER))

    for node in tree.body:
        names: list[str] = []
        value_node = None

        if isinstance(node, ast.Assign):
            names = [
                target.id
                for target in node.targets
                if isinstance(target, ast.Name)
            ]
            value_node = node.value

        elif isinstance(node, ast.AnnAssign):
            if isinstance(node.target, ast.Name):
                names = [node.target.id]
            value_node = node.value

        else:
            continue

        if variable_name not in names:
            continue

        if value_node is None:
            return set()

        # Для registry вида:
        # SIGNAL_BUILDERS = {
        #     "ATR_IMPULSE_V1": atr_impulse_signal,
        #     ...
        # }
        # значения являются ссылками на функции и не подходят
        # для ast.literal_eval(). Нам нужны только строковые ключи.
        if isinstance(value_node, ast.Dict):
            result: set[str] = set()

            for key_node in value_node.keys:
                if (
                    isinstance(key_node, ast.Constant)
                    and isinstance(key_node.value, str)
                ):
                    result.add(key_node.value)

            return result

        try:
            value = ast.literal_eval(value_node)
        except (ValueError, TypeError):
            return set()

        if isinstance(value, (set, tuple, list)):
            return {str(item) for item in value}

    return set()


def main() -> int:
    source = ADAPTER.read_text(
        encoding="utf-8",
        errors="replace",
    )

    supported = literal_string_collection(
        source,
        "SUPPORTED_STRATEGIES",
    )

    registered = literal_string_collection(
        source,
        "SIGNAL_BUILDERS",
    )

    executable = supported & registered

    with psycopg2.connect(build_psycopg_url()) as conn:
        conn.set_session(readonly=True)

        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cursor:
            cursor.execute(
                """
                SELECT
                    r.strategy_code,
                    r.timeframe,
                    count(DISTINCT r.run_uuid)::bigint
                        AS template_run_count,
                    count(*) FILTER (
                        WHERE r.parameter_json IS NOT NULL
                    )::bigint AS parameterized_run_count,
                    max(r.created_at) AS latest_run_at
                FROM analytics.edge_lab_run_v1 r
                WHERE r.symbol = 'NG@RTSX'
                  AND r.strategy_code = ANY(%s)
                GROUP BY
                    r.strategy_code,
                    r.timeframe
                ORDER BY
                    r.strategy_code,
                    r.timeframe
                """,
                (sorted(executable),),
            )

            rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

            cursor.execute(
                """
                SELECT
                    timeframe,
                    count(*)::bigint AS bar_count,
                    min(ts) AS first_ts,
                    max(ts) AS last_ts
                FROM public.market_bars
                WHERE symbol = 'NGZ6@RTSX'
                GROUP BY timeframe
                ORDER BY timeframe
                """
            )

            bar_rows = [
                dict(row)
                for row in cursor.fetchall()
            ]

    bars_by_timeframe = {
        str(row["timeframe"]): row
        for row in bar_rows
    }

    eligible: list[dict[str, Any]] = []

    for row in rows:
        coverage = bars_by_timeframe.get(
            str(row["timeframe"])
        )

        if coverage is None:
            continue

        if int(coverage["bar_count"] or 0) < 100:
            continue

        if int(row["parameterized_run_count"] or 0) == 0:
            continue

        eligible.append(
            {
                **row,
                "bar_count": coverage["bar_count"],
                "bar_first_ts": coverage["first_ts"],
                "bar_last_ts": coverage["last_ts"],
            }
        )

    print(
        "=== POSTGRESQL FUTURES SUPPORTED "
        "STRATEGY TEMPLATE V1 ==="
    )
    print(
        "supported_strategies="
        + ",".join(sorted(supported))
    )
    print(
        "registered_signal_strategies="
        + ",".join(sorted(registered))
    )
    print(
        "executable_strategies="
        + ",".join(sorted(executable))
    )
    print(f"template_group_count={len(rows)}")
    print(f"eligible_template_count={len(eligible)}")

    for row in eligible:
        print(
            "ELIGIBLE_TEMPLATE "
            f"strategy={row['strategy_code']} "
            f"timeframe={row['timeframe']} "
            f"template_runs={row['template_run_count']} "
            f"parameterized_runs="
            f"{row['parameterized_run_count']} "
            f"bars={row['bar_count']} "
            f"bar_first_ts={row['bar_first_ts']} "
            f"bar_last_ts={row['bar_last_ts']} "
            f"latest_run_at={row['latest_run_at']}"
        )

    print("db_writes_performed=0")
    print("strategy_changed=0")
    print("risk_engine_changed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if not eligible:
        print(
            "root_cause="
            "SUPPORTED_FUTURES_TEMPLATE_NOT_FOUND"
        )
        print(
            "VERDICT="
            "POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_BLOCKED"
        )
        return 2

    print(
        "recommended_strategy="
        f"{eligible[0]['strategy_code']}"
    )
    print(
        "recommended_timeframe="
        f"{eligible[0]['timeframe']}"
    )
    print(
        "root_cause="
        "SUPPORTED_FUTURES_TEMPLATE_FOUND"
    )
    print(
        "VERDICT="
        "POSTGRESQL_FUTURES_SUPPORTED_STRATEGY_TEMPLATE_V1_READY"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
