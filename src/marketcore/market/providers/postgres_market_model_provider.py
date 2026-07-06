from __future__ import annotations

from datetime import datetime

from marketcore.market.dto import MarketSnapshotDTO
from marketcore.market.interfaces import MarketModelProvider
from marketcore.market.mapper import MarketSnapshotMapper
from marketcore.market.repository import MarketModelRepository


class PostgresMarketModelProvider(MarketModelProvider):
    def __init__(
        self,
        repository: MarketModelRepository | None = None,
        mapper: MarketSnapshotMapper | None = None,
    ) -> None:
        self._repository = repository or MarketModelRepository()
        self._mapper = mapper or MarketSnapshotMapper()

    def load(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> MarketSnapshotDTO:
        raw = self._repository.load_raw(
            symbol=symbol,
            broker_code=broker_code,
            account_scope=account_scope,
            snapshot_ts=snapshot_ts,
        )
        return self._mapper.build_snapshot(
            raw_record=raw,
            broker_code=broker_code,
            account_scope=account_scope,
            snapshot_ts=snapshot_ts,
        )

    def load_many(
        self,
        symbols: list[str],
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> dict[str, MarketSnapshotDTO]:
        return {
            symbol: self.load(
                symbol=symbol,
                broker_code=broker_code,
                account_scope=account_scope,
                snapshot_ts=snapshot_ts,
            )
            for symbol in symbols
        }
