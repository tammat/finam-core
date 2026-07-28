from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from finam_core.data.runtime_universe_provider import RuntimeUniverseProvider


@dataclass(frozen=True)
class RuntimeSymbolReloadDecision:
    active_symbols: list[str]
    added_symbols: list[str]
    removed_symbols: list[str]


class RuntimeSymbolReloadService:
    """Русский комментарий: сравнивает текущую подписку с runtime-universe из dynamic_watchlist."""

    def __init__(
        self,
        pg_logger: Any,
        source: str = "opportunity_scanner",
        limit: int = 10,
        sources: list[str] | None = None,
    ) -> None:
        self.provider = RuntimeUniverseProvider(pg_logger)
        self.source = source
        self.sources = sources or [source, "confirmation_universe"]
        self.limit = int(limit)

    def decide(self, current_symbols: list[str]) -> RuntimeSymbolReloadDecision:
        current = list(dict.fromkeys([s for s in current_symbols if s]))
        desired = self.provider.load_symbols(
            source=self.source,
            sources=self.sources,
            limit=self.limit,
        )

        # Провайдер уже возвращает DB-приоритет: сначала перспективные и
        # недозаполненные исследовательские связки. Подписка Finam имеет жёсткий
        # лимит символов, поэтому расширять её объединением двух списков нельзя.
        # Остаток лимита заполняем текущими символами, чтобы переход был плавным.
        active = list(dict.fromkeys(desired + current))[: self.limit]

        current_set = set(current)
        added = [s for s in desired if s not in current_set]

        removed = [s for s in current if s not in set(active)]

        return RuntimeSymbolReloadDecision(
            active_symbols=active,
            added_symbols=added,
            removed_symbols=removed,
        )
