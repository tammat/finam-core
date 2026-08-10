from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class RealCandidateIdentityV1:
    observation_uuid: UUID
    strategy_code: str
    symbol: str
    timeframe: str
    parameter_hash: str
    discovery_batch_id: str


def candidate_identity_from_row(
    row,
) -> RealCandidateIdentityV1:
    return RealCandidateIdentityV1(
        observation_uuid=UUID(
            str(row["observation_uuid"])
        ),
        strategy_code=str(
            row["strategy_code"]
        ),
        symbol=str(
            row["symbol"]
        ),
        timeframe=str(
            row["timeframe"]
        ),
        parameter_hash=str(
            row["parameter_hash"]
        ),
        discovery_batch_id=str(
            row["discovery_batch_id"]
        ),
    )
