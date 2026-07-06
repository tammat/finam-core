from __future__ import annotations

from datetime import datetime
from typing import Protocol

from marketcore.market.dto import MarketSnapshotDTO


class MarketModelProvider(Protocol):
    def load(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> MarketSnapshotDTO:
        ...

    def load_many(
        self,
        symbols: list[str],
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> dict[str, MarketSnapshotDTO]:
        ...
