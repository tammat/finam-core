from __future__ import annotations

from datetime import datetime

from marketcore.market.cache import MarketModelCache
from marketcore.market.dto import MarketSnapshotDTO
from marketcore.market.providers import PostgresMarketModelProvider


class MarketModelResolver:
    def __init__(
        self,
        provider: PostgresMarketModelProvider | None = None,
        cache: MarketModelCache | None = None,
    ) -> None:
        self._provider = provider or PostgresMarketModelProvider()
        self._cache = cache or MarketModelCache()

    def _cache_key(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None,
    ) -> str:
        ts_key = snapshot_ts.isoformat() if snapshot_ts else "LATEST"
        return f"{symbol}|{broker_code}|{account_scope}|{ts_key}"

    def resolve(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
        refresh: bool = False,
    ) -> MarketSnapshotDTO:
        key = self._cache_key(symbol, broker_code, account_scope, snapshot_ts)

        if not refresh:
            cached = self._cache.get(key)
            if cached is not None:
                return cached

        snapshot = self._provider.load(
            symbol=symbol,
            broker_code=broker_code,
            account_scope=account_scope,
            snapshot_ts=snapshot_ts,
        )

        self._cache.put(key, snapshot)
        return snapshot

    def resolve_many(
        self,
        symbols: list[str],
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
        refresh: bool = False,
    ) -> dict[str, MarketSnapshotDTO]:
        return {
            symbol: self.resolve(
                symbol=symbol,
                broker_code=broker_code,
                account_scope=account_scope,
                snapshot_ts=snapshot_ts,
                refresh=refresh,
            )
            for symbol in symbols
        }

    def invalidate(
        self,
        symbol: str,
        broker_code: str,
        account_scope: str,
        snapshot_ts: datetime | None = None,
    ) -> None:
        self._cache.invalidate(
            self._cache_key(symbol, broker_code, account_scope, snapshot_ts)
        )

    def clear(self) -> None:
        self._cache.clear()
