from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from pathlib import Path

from marketcore.research.economics.economic_cost_gate_v1 import (
    EconomicCostGatePolicyV1,
)


EXPECTED_SOURCE_VERSION = "ECONOMIC_COST_GATE_POLICY_V1"


class EconomicCostGatePolicyLoadErrorV1(RuntimeError):
    pass


def load_economic_cost_gate_policy_v1(
    path: Path,
) -> EconomicCostGatePolicyV1:
    if not path.is_file():
        raise EconomicCostGatePolicyLoadErrorV1(
            f"ECONOMIC_COST_GATE_POLICY_FILE_NOT_FOUND:{path}"
        )

    try:
        payload = json.loads(
            path.read_text(encoding="utf-8")
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_INVALID_JSON"
        ) from exc

    required = {
        "minimum_trades",
        "minimum_net_expectancy",
        "minimum_net_profit_factor",
        "source_version",
    }

    missing = sorted(required - payload.keys())

    if missing:
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_FIELDS_MISSING:"
            + ",".join(missing)
        )

    if payload["source_version"] != EXPECTED_SOURCE_VERSION:
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_VERSION_MISMATCH:"
            f"{payload['source_version']}"
        )

    try:
        minimum_trades = int(payload["minimum_trades"])
        minimum_net_expectancy = Decimal(
            str(payload["minimum_net_expectancy"])
        )
        minimum_net_profit_factor = Decimal(
            str(payload["minimum_net_profit_factor"])
        )
    except (TypeError, ValueError, InvalidOperation) as exc:
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_VALUE_INVALID"
        ) from exc

    if minimum_trades < 1:
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_MINIMUM_TRADES_INVALID"
        )

    if not minimum_net_expectancy.is_finite():
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_EXPECTANCY_NOT_FINITE"
        )

    if (
        not minimum_net_profit_factor.is_finite()
        or minimum_net_profit_factor < Decimal("0")
    ):
        raise EconomicCostGatePolicyLoadErrorV1(
            "ECONOMIC_COST_GATE_POLICY_PROFIT_FACTOR_INVALID"
        )

    return EconomicCostGatePolicyV1(
        minimum_trades=minimum_trades,
        minimum_net_expectancy=minimum_net_expectancy,
        minimum_net_profit_factor=minimum_net_profit_factor,
    )
