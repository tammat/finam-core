from __future__ import annotations

from collections import OrderedDict

from marketcore.market.dto import MarketSnapshotDTO


class MarketModelCache:
    """
    LRU cache для MarketSnapshotDTO.
    Не содержит SQL и не знает о Provider.
    """

    def __init__(self, max_size: int = 2048) -> None:
        self._max_size = max_size
        self._cache: OrderedDict[str, MarketSnapshotDTO] = OrderedDict()

    def get(self, key: str) -> MarketSnapshotDTO | None:
        value = self._cache.get(key)

        if value is None:
            return None

        self._cache.move_to_end(key)

        return value

    def put(
        self,
        key: str,
        snapshot: MarketSnapshotDTO,
    ) -> None:

        self._cache[key] = snapshot
        self._cache.move_to_end(key)

        while len(self._cache) > self._max_size:
            self._cache.popitem(last=False)

    def invalidate(
        self,
        key: str,
    ) -> None:
        self._cache.pop(key, None)

    def clear(self) -> None:
        self._cache.clear()

    def size(self) -> int:
        return len(self._cache)
