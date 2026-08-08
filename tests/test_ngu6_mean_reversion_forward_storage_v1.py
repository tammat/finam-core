import importlib.util
import sys
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    CANDIDATE_CODE,
    ContractSpecSnapshot,
    ForwardObservation,
    ForwardObserverContractError,
)


RUNNER_PATH = Path(
    "scripts/research/"
    "run_ngu6_mean_reversion_forward_observer_v1.py"
)

MODULE_NAME = "ngu6_forward_runner_test"

spec = importlib.util.spec_from_file_location(
    MODULE_NAME,
    RUNNER_PATH,
)

assert spec is not None
assert spec.loader is not None

runner = importlib.util.module_from_spec(spec)
sys.modules[MODULE_NAME] = runner
spec.loader.exec_module(runner)


class FakeCursor:
    def __init__(self, fetches=None):
        self.fetches = list(fetches or [])
        self.executions = []

    def execute(self, query, values=None):
        self.executions.append(
            (str(query), values)
        )

    def fetchall(self):
        if not self.fetches:
            return []

        value = self.fetches.pop(0)

        if isinstance(value, list):
            return value

        return [value]

    def fetchone(self):
        if not self.fetches:
            return None

        value = self.fetches.pop(0)

        if isinstance(value, list):
            return value[0] if value else None

        return value


def make_spec():
    ts = datetime(
        2026, 8, 8, 7, 0, 38,
        tzinfo=timezone.utc,
    )

    return ContractSpecSnapshot(
        contract_spec_id=219,
        valid_from=ts,
        valid_to=None,
        tick_size=Decimal("0.001"),
        tick_value=Decimal("8.21665"),
        contract_multiplier=Decimal("8216.65"),
        source_version="MOEX_ISS_CONTRACT_SPEC_V1",
    )


def make_observation(status="CLOSED"):
    signal_ts = datetime(
        2026, 8, 8, 8, 0,
        tzinfo=timezone.utc,
    )

    closed = status == "CLOSED"

    return ForwardObservation(
        candidate_code=CANDIDATE_CODE,
        signal_ts=signal_ts,
        side="LONG",
        market_entry_price=Decimal("3.000"),
        entry_price=Decimal("3.0006"),
        exit_ts=(
            signal_ts + timedelta(minutes=25)
            if closed else None
        ),
        market_exit_price=(
            Decimal("3.020")
            if closed else None
        ),
        exit_price=(
            Decimal("3.019396")
            if closed else None
        ),
        gross_pnl=(
            Decimal("154.4")
            if closed else None
        ),
        commission=(
            Decimal("3.88")
            if closed else None
        ),
        slippage=(
            Decimal("9.6")
            if closed else None
        ),
        net_pnl=(
            Decimal("150.52")
            if closed else None
        ),
        ac100=Decimal("-0.12"),
        contract_spec=make_spec(),
        status=status,
    )


def test_ddl_has_hard_safety_constraints():
    ddl = runner.DDL.lower()

    assert "check (shadow_only)" in ddl
    assert "check (not broker_order_sent)" in ddl
    assert "check (not runtime_allowed)" in ddl
    assert "check (not execution_enabled)" in ddl

    assert "unique(candidate_code, signal_ts)" in ddl


def test_contract_spec_interval_resolution_exactly_one():
    row = {
        "id": 219,
        "valid_from": datetime(
            2026, 8, 8, 7, 0, 38,
            tzinfo=timezone.utc,
        ),
        "valid_to": None,
        "tick_size": Decimal("0.001"),
        "tick_value": Decimal("8.21665"),
        "contract_multiplier": Decimal("8216.65"),
        "source_version": "MOEX_ISS_CONTRACT_SPEC_V1",
    }

    cursor = FakeCursor(fetches=[[row]])

    signal_ts = datetime(
        2026, 8, 8, 8, 0,
        tzinfo=timezone.utc,
    )

    result = runner.load_contract_spec_at(
        cursor,
        signal_ts,
    )

    assert result.contract_spec_id == 219
    assert result.contract_multiplier == Decimal("8216.65")

    query, values = cursor.executions[0]

    assert "valid_from <= %s" in query
    assert "valid_to is null" in query.lower()
    assert values == (
        runner.SYMBOL,
        signal_ts,
        signal_ts,
    )


@pytest.mark.parametrize(
    "rows",
    (
        [],
        [
            {
                "id": 1,
                "valid_from": datetime.now(timezone.utc),
                "valid_to": None,
                "tick_size": 1,
                "tick_value": 1,
                "contract_multiplier": 1,
                "source_version": "A",
            },
            {
                "id": 2,
                "valid_from": datetime.now(timezone.utc),
                "valid_to": None,
                "tick_size": 1,
                "tick_value": 1,
                "contract_multiplier": 1,
                "source_version": "B",
            },
        ],
    ),
)
def test_contract_spec_resolution_fails_closed(rows):
    cursor = FakeCursor(fetches=[rows])

    with pytest.raises(
        ForwardObserverContractError,
        match="contract_spec_interval_resolution_failed",
    ):
        runner.load_contract_spec_at(
            cursor,
            datetime(
                2026, 8, 8, 8, 0,
                tzinfo=timezone.utc,
            ),
        )


def test_closed_existing_observation_is_immutable():
    cursor = FakeCursor(
        fetches=[
            {
                "observation_status": "CLOSED",
            }
        ]
    )

    inserted, updated = runner.upsert_observation(
        cursor,
        make_observation("CLOSED"),
    )

    assert inserted is False
    assert updated is False

    # Только SELECT ... FOR UPDATE.
    assert len(cursor.executions) == 1


def test_open_to_open_does_not_rewrite_snapshot():
    cursor = FakeCursor(
        fetches=[
            {
                "observation_status": "OPEN",
            }
        ]
    )

    inserted, updated = runner.upsert_observation(
        cursor,
        make_observation("OPEN"),
    )

    assert inserted is False
    assert updated is False
    assert len(cursor.executions) == 1


def test_open_to_closed_is_only_allowed_update():
    cursor = FakeCursor(
        fetches=[
            {
                "observation_status": "OPEN",
            }
        ]
    )

    inserted, updated = runner.upsert_observation(
        cursor,
        make_observation("CLOSED"),
    )

    assert inserted is False
    assert updated is True
    assert len(cursor.executions) == 2

    query, values = cursor.executions[1]

    assert "on conflict" in query.lower()
    assert "contract_spec_id = excluded" not in query.lower()

    # Snapshot identity remains the original INSERT identity;
    # conflict update changes only exit/PnL/status/safety fields.
    assert values[0] == CANDIDATE_CODE


def test_new_observation_uses_hardcoded_safe_flags():
    cursor = FakeCursor(fetches=[None])

    inserted, updated = runner.upsert_observation(
        cursor,
        make_observation("OPEN"),
    )

    assert inserted is True
    assert updated is False
    assert len(cursor.executions) == 2

    query, _ = cursor.executions[1]
    normalized = " ".join(query.lower().split())

    assert "true,false,false,false" in normalized
