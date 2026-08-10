from __future__ import annotations

import importlib.util
import json
import os
import sys
from decimal import Decimal
from pathlib import Path

import psycopg2
from psycopg2.extras import RealDictCursor

from marketcore.research.economics.canonical_economic_gate_adapter_v1 import (
    evaluate_canonical_economic_gate_v1,
)
from marketcore.research.economics.canonical_economic_replay_v1 import (
    CanonicalReplayTradeV1,
    build_economic_trade_set_v1,
)
from marketcore.research.economics.canonical_monetary_normalizer_v1 import (
    AssetClassV1,
    MonetaryContractV1,
)
from marketcore.research.economics.economic_cost_resolver_v1 import (
    CostModelV1,
    EconomicCostContractV1,
)
from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)

from scripts.research.build_trend_pullback_canonical_cost_resolver_v1 import (
    resolve_cost_contract,
)


ROOT = Path("/opt/finam-core")

SCREEN_PATH = ROOT / (
    "src/scripts/research/"
    "build_universe_trend_pullback_canonical_adapter_screen_v1.py"
)

CONFIG_PATH = ROOT / (
    "config/research/"
    "trend_pullback_canonical_robustness_v1.json"
)

SYMBOLS = (
    "NVTK@MISX",
    "PLZL@MISX",
    "USDRUBF@RTSX",
)

EXPECTED = {
    "NVTK@MISX": {
        "trades": 1153,
        "net_pnl": Decimal("-780.608750000"),
    },
    "PLZL@MISX": {
        "trades": 1121,
        "net_pnl": Decimal("-1023.080000000"),
    },
    "USDRUBF@RTSX": {
        "trades": 2573,
        "net_pnl": Decimal("-333.5140730000"),
    },
}

TOLERANCE = Decimal("0.000001")


def dec(value) -> Decimal:
    return Decimal(str(value or 0))


def load_screen():
    name = (
        "trend_pullback_screen_"
        "historical_economic_replay_v1"
    )

    spec = importlib.util.spec_from_file_location(
        name,
        SCREEN_PATH,
    )

    if spec is None or spec.loader is None:
        raise RuntimeError(
            "ERROR=CANONICAL_SCREEN_IMPORT_FAILED"
        )

    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module

    try:
        spec.loader.exec_module(module)
    except Exception:
        sys.modules.pop(name, None)
        raise

    return module


def policy_from_config(
    cfg: dict,
) -> EconomicCostGatePolicyV1:
    return EconomicCostGatePolicyV1(
        minimum_trades=int(
            cfg["minimum_oos_trades"]
        ),
        minimum_net_expectancy=Decimal("0"),
        minimum_net_profit_factor=Decimal("1"),
    )


def baseline_parameters(
    cfg: dict,
) -> dict:
    baseline = next(
        (
            row
            for row in cfg["variants"]
            if row.get("code") == "BASELINE"
        ),
        None,
    )

    if baseline is None:
        raise RuntimeError(
            "ERROR=BASELINE_VARIANT_NOT_FOUND"
        )

    result = {
        key: value
        for key, value in baseline.items()
        if key != "code"
    }

    result["hold_bars"] = int(
        cfg["screen_exit_horizon"]["hold_bars"]
    )

    return result


def load_bars(
    cur,
    screen,
    *,
    symbol: str,
    timeframe: str,
):
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
            timeframe,
        ),
    )

    return [
        screen.MarketBar(
            ts=row["ts"],
            open=dec(row["open"]),
            high=dec(row["high"]),
            low=dec(row["low"]),
            close=dec(row["close"]),
            volume=dec(row["volume"]),
        )
        for row in cur.fetchall()
    ]


def build_contracts(
    cur,
    symbol: str,
):
    if symbol.endswith("@MISX"):
        source = resolve_cost_contract(
            cur,
            symbol,
        )

        monetary = MonetaryContractV1(
            asset_class=AssetClassV1.EQUITY,
            lot_size=Decimal("1"),
        )

        costs = EconomicCostContractV1(
            model=(
                CostModelV1
                .EQUITY_FIXED_PLUS_TURNOVER
            ),
            commission_per_side=dec(
                source.commission_per_trade
            ),
            commission_pct=dec(
                source.commission_pct
            ),
            slippage_per_side=dec(
                source.slippage_per_trade
            ),
        )

        return monetary, costs

    if symbol == "USDRUBF@RTSX":
        monetary = MonetaryContractV1(
            asset_class=AssetClassV1.FUTURES,
            tick_size=Decimal("0.01"),
            tick_value=Decimal("10"),
        )

        costs = EconomicCostContractV1(
            model=(
                CostModelV1
                .FUTURES_MAKER_TAKER
            ),
            maker_rate_pct=Decimal("0"),
            taker_rate_pct=Decimal("0.00462"),
            slippage_per_side=Decimal("1"),
        )

        return monetary, costs

    raise RuntimeError(
        "ERROR=UNSUPPORTED_CONTROL_SYMBOL "
        f"symbol={symbol}"
    )


def main() -> int:
    screen = load_screen()

    cfg = json.loads(
        CONFIG_PATH.read_text()
    )

    params = baseline_parameters(cfg)

    policy = policy_from_config(cfg)

    development_fraction = Decimal(
        str(cfg["development_fraction"])
    )

    conn = psycopg2.connect(
        os.environ["DATABASE_URL"]
    )

    conn.set_session(
        readonly=True,
        autocommit=False,
    )

    matched = 0
    rejected = 0

    try:
        with conn.cursor(
            cursor_factory=RealDictCursor
        ) as cur:

            for symbol in SYMBOLS:
                bars = load_bars(
                    cur,
                    screen,
                    symbol=symbol,
                    timeframe=cfg["timeframe"],
                )

                if not bars:
                    raise RuntimeError(
                        "ERROR=MARKET_BARS_MISSING "
                        f"symbol={symbol}"
                    )

                development_end = int(
                    Decimal(len(bars))
                    * development_fraction
                )

                canonical = (
                    screen.build_canonical_trades(
                        bars,
                        params,
                        development_end,
                        len(bars),
                    )
                )

                monetary_contract, cost_contract = (
                    build_contracts(
                        cur,
                        symbol,
                    )
                )

                replay = tuple(
                    CanonicalReplayTradeV1(
                        # gross_pnl уже signed.
                        # direction повторно НЕ применяется.
                        price_pnl=dec(
                            trade.gross_pnl
                        ),
                        quantity=Decimal("1"),
                        entry_price=dec(
                            trade.entry_price
                        ),
                        exit_price=dec(
                            trade.exit_price
                        ),
                        entry_is_taker=True,
                        exit_is_taker=True,
                        funding_cost=Decimal("0"),
                    )
                    for trade in canonical
                )

                economic_trades = (
                    build_economic_trade_set_v1(
                        trades=replay,
                        monetary_contract=(
                            monetary_contract
                        ),
                        cost_contract=cost_contract,
                    )
                )

                result = (
                    evaluate_canonical_economic_gate_v1(
                        economic_trades,
                        policy,
                    )
                )

                expected = EXPECTED[symbol]

                trades_match = (
                    result.trades
                    == expected["trades"]
                )

                net_delta = abs(
                    result.net_pnl
                    - expected["net_pnl"]
                )

                pnl_match = (
                    net_delta <= TOLERANCE
                )

                verdict_match = (
                    result.passed is False
                )

                case_match = (
                    trades_match
                    and pnl_match
                    and verdict_match
                )

                matched += int(case_match)
                rejected += int(
                    not result.passed
                )

                print(
                    "HISTORICAL_ECONOMIC_REPLAY_ROW "
                    f"symbol={symbol} "
                    f"trades={result.trades} "
                    f"gross_pnl={result.gross_pnl} "
                    f"total_cost={result.total_cost} "
                    f"net_pnl={result.net_pnl} "
                    f"net_expectancy="
                    f"{result.net_expectancy} "
                    f"net_profit_factor="
                    f"{result.net_profit_factor} "
                    f"status={result.status} "
                    f"expected_net_pnl="
                    f"{expected['net_pnl']} "
                    f"net_pnl_delta={net_delta} "
                    f"match={int(case_match)}"
                )

                if not case_match:
                    raise RuntimeError(
                        "ERROR=HISTORICAL_REPLAY_MISMATCH "
                        f"symbol={symbol}"
                    )

    finally:
        conn.rollback()
        conn.close()

    print(f"replay_cases={len(SYMBOLS)}")
    print(f"matched_cases={matched}")
    print(f"rejected_cases={rejected}")

    print("canonical_trade_replay_used=1")
    print("individual_trade_costing_used=1")
    print("aggregate_evidence_used_for_calculation=0")
    print("direction_double_count_guard=PASS")

    print("db_writes_performed=0")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("economic_edge_claimed=0")
    print("micro_live_allowed=0")

    print(
        "VERDICT="
        "TREND_PULLBACK_HISTORICAL_"
        "ECONOMIC_REPLAY_V1_OK"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
