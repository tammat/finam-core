from __future__ import annotations

import hashlib
import os
import re
import subprocess
import sys
import uuid
from decimal import Decimal

import psycopg2


SOURCE_VERSION = (
    "TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1"
)

CALCULATOR = (
    "src/scripts/research/"
    "build_trend_pullback_canonical_equity_base_cost_validation_v1.py"
)

ROW_RE = re.compile(
    r"^EQUITY_BASE_COST_ROW "
    r"symbol=(?P<symbol>\S+) "
    r"trades=(?P<trades>\d+) "
    r"gross_pnl=(?P<gross_pnl>\S+) "
    r"gross_pf=(?P<gross_pf>\S+) "
    r"gross_expectancy=(?P<gross_expectancy>\S+) "
    r"commission=(?P<commission>\S+) "
    r"slippage=(?P<slippage>\S+) "
    r"total_cost=(?P<total_cost>\S+) "
    r"net_pnl=(?P<net_pnl>\S+) "
    r"net_expectancy=(?P<net_expectancy>\S+) "
    r"net_profit_factor=(?P<net_profit_factor>\S+) "
    r"net_winrate=(?P<net_winrate>\S+) "
    r"max_drawdown=(?P<max_drawdown>\S+) "
    r"cost_to_gross_ratio=(?P<cost_to_gross_ratio>\S+) "
    r"survive_after_base_costs=(?P<survive>[01])$"
)


def dec(value: str) -> Decimal:
    return Decimal(value)


def run_calculator() -> str:
    result = subprocess.run(
        [
            sys.executable,
            "-u",
            CALCULATOR,
        ],
        check=False,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "PYTHONPATH": "src",
        },
    )

    if result.returncode != 0:
        sys.stderr.write(result.stderr)

        raise RuntimeError(
            "ERROR=EQUITY_BASE_COST_CALCULATOR_FAILED "
            f"exit_code={result.returncode}"
        )

    return result.stdout


def parse_rows(output: str) -> list[dict]:
    rows: list[dict] = []

    for line in output.splitlines():
        match = ROW_RE.match(line.strip())

        if not match:
            continue

        item = match.groupdict()

        survive = item["survive"] == "1"

        rows.append(
            {
                "symbol": item["symbol"],
                "trades": int(item["trades"]),
                "gross_pnl": dec(item["gross_pnl"]),
                "gross_profit_factor": dec(item["gross_pf"]),
                "gross_expectancy": dec(
                    item["gross_expectancy"]
                ),
                "commission": dec(item["commission"]),
                "slippage": dec(item["slippage"]),
                "total_cost": dec(item["total_cost"]),
                "net_pnl": dec(item["net_pnl"]),
                "net_expectancy": dec(
                    item["net_expectancy"]
                ),
                "net_profit_factor": dec(
                    item["net_profit_factor"]
                ),
                "net_winrate": dec(item["net_winrate"]),
                "max_drawdown": dec(
                    item["max_drawdown"]
                ),
                "cost_to_gross_ratio": dec(
                    item["cost_to_gross_ratio"]
                ),
                "cost_validation_status": (
                    "SURVIVE_AFTER_BASE_COSTS"
                    if survive
                    else "REJECT_AFTER_BASE_COSTS"
                ),
                "economic_edge_claimed": False,
                "micro_live_allowed": False,
            }
        )

    return rows


def main() -> int:
    dsn = os.environ.get("DATABASE_URL")

    if not dsn:
        raise SystemExit(
            "ERROR=DATABASE_URL_NOT_SET"
        )

    output = run_calculator()

    required_contract = (
        "SUMMARY_ROW symbols=2 survivors=0",
        "base_costs_used=1",
        "execution_spread_impact_used=0",
        "economic_edge_claimed=0",
        "micro_live_allowed=0",
        "VERDICT="
        "TREND_PULLBACK_CANONICAL_EQUITY_BASE_COST_VALIDATION_V1_READY",
    )

    for required in required_contract:
        if required not in output:
            raise SystemExit(
                "ERROR=CALCULATOR_CONTRACT_MISSING "
                f"value={required}"
            )

    rows = parse_rows(output)

    if len(rows) != 2:
        raise SystemExit(
            "ERROR=UNEXPECTED_EQUITY_COST_ROW_COUNT "
            f"rows={len(rows)}"
        )

    expected_symbols = {
        "NVTK@MISX",
        "PLZL@MISX",
    }

    actual_symbols = {
        row["symbol"]
        for row in rows
    }

    if actual_symbols != expected_symbols:
        raise SystemExit(
            "ERROR=UNEXPECTED_EQUITY_SYMBOL_SET "
            f"symbols={sorted(actual_symbols)}"
        )

    if any(
        row["cost_validation_status"]
        != "REJECT_AFTER_BASE_COSTS"
        for row in rows
    ):
        raise SystemExit(
            "ERROR=UNEXPECTED_EQUITY_SURVIVOR"
        )

    output_hash = hashlib.sha256(
        output.encode("utf-8")
    ).hexdigest()

    run_uuid = uuid.uuid5(
        uuid.NAMESPACE_URL,
        "marketcore:"
        + SOURCE_VERSION
        + ":"
        + output_hash,
    )

    inserted = 0

    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            for row in rows:
                cur.execute(
                    """
                    INSERT INTO
                    analytics.trend_pullback_equity_base_cost_validation_v1
                    (
                        run_uuid,
                        symbol,
                        strategy_code,
                        timeframe,
                        trades,
                        gross_pnl,
                        gross_profit_factor,
                        gross_expectancy,
                        commission,
                        slippage,
                        total_cost,
                        net_pnl,
                        net_expectancy,
                        net_profit_factor,
                        net_winrate,
                        max_drawdown,
                        cost_to_gross_ratio,
                        cost_validation_status,
                        economic_edge_claimed,
                        micro_live_allowed,
                        source_version
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        'TREND_PULLBACK_V1',
                        'M5',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        false,
                        false,
                        %s
                    )
                    ON CONFLICT (run_uuid, symbol)
                    DO NOTHING
                    """,
                    (
                        str(run_uuid),
                        row["symbol"],
                        row["trades"],
                        row["gross_pnl"],
                        row["gross_profit_factor"],
                        row["gross_expectancy"],
                        row["commission"],
                        row["slippage"],
                        row["total_cost"],
                        row["net_pnl"],
                        row["net_expectancy"],
                        row["net_profit_factor"],
                        row["net_winrate"],
                        row["max_drawdown"],
                        row["cost_to_gross_ratio"],
                        row["cost_validation_status"],
                        SOURCE_VERSION,
                    ),
                )

                inserted += cur.rowcount

    print(f"run_uuid={run_uuid}")
    print(f"rows_parsed={len(rows)}")
    print(f"rows_inserted={inserted}")
    print("equity_survivors=0")
    print("economic_edge_claimed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "TREND_PULLBACK_EQUITY_BASE_COST_PERSISTED_V1"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
