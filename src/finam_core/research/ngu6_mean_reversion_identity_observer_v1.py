from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Sequence

from finam_core.research.ngu6_mean_reversion_forward_observer_v1 import (
    CANDIDATE_CODE,
    FORWARD_BOUNDARY,
    FROZEN_PARAMETERS,
    HOLD_BARS,
    ContractSpecSnapshot,
    ForwardObserverContractError,
    mean_reversion_zscore_signal,
)
from finam_core.research.postgresql_edge_backtest_adapter_v1 import Bar


SOURCE_VERSION = "NGU6_MEAN_REVERSION_IDENTITY_OBSERVER_V1"


@dataclass(frozen=True, slots=True)
class IdentityObservation:
    candidate_code: str
    signal_ts: datetime
    side: str
    exit_ts: datetime | None
    contract_spec_id: int
    status: str


def build_identity_observations(
    bars: Sequence[Bar],
    contract_specs_by_ts: dict[datetime, ContractSpecSnapshot],
    *,
    boundary: datetime = FORWARD_BOUNDARY,
) -> list[IdentityObservation]:
    """
    Build frozen NGU6 mean-reversion trade identities only.

    This function intentionally does NOT compute or expose:
    - market prices;
    - execution prices;
    - gross PnL;
    - commission;
    - slippage;
    - net PnL.

    Position overlap semantics are identical to the frozen historical /
    forward observer:
        after a signal, the next eligible signal is searched only after
        exit_index + 1.
    """
    observations: list[IdentityObservation] = []

    index = 1

    while index < len(bars):
        bar = bars[index]

        # History before/equal to the frozen boundary is warm-up only.
        if bar.ts <= boundary:
            index += 1
            continue

        signal = mean_reversion_zscore_signal(
            bars,
            index,
            FROZEN_PARAMETERS,
        )

        if signal is None:
            index += 1
            continue

        contract_spec = contract_specs_by_ts.get(bar.ts)

        if contract_spec is None:
            raise ForwardObserverContractError(
                f"contract_spec_missing:{bar.ts.isoformat()}"
            )

        exit_index = index + HOLD_BARS

        if exit_index >= len(bars):
            observations.append(
                IdentityObservation(
                    candidate_code=CANDIDATE_CODE,
                    signal_ts=bar.ts,
                    side=signal,
                    exit_ts=None,
                    contract_spec_id=(
                        contract_spec.contract_spec_id
                    ),
                    status="OPEN",
                )
            )
            break

        exit_bar = bars[exit_index]

        observations.append(
            IdentityObservation(
                candidate_code=CANDIDATE_CODE,
                signal_ts=bar.ts,
                side=signal,
                exit_ts=exit_bar.ts,
                contract_spec_id=(
                    contract_spec.contract_spec_id
                ),
                status="CLOSED",
            )
        )

        # Frozen no-overlap semantics.
        index = exit_index + 1

    return observations
