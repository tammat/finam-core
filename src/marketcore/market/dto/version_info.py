from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID


@dataclass(frozen=True, slots=True)
class VersionInfoDTO:
    snapshot_uuid: UUID
    market_model_version: str
    schema_version: str
    data_version: str
    snapshot_ts: datetime
    source_version: str
