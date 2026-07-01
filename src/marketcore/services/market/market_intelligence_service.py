from __future__ import annotations

from marketcore.presentation.viewmodels.market_intelligence_vm import (
    MarketIntelligenceVM,
    build_default_market_intelligence_vm,
)


class MarketIntelligenceService:
    """
    V1:
    Использует существующие провайдеры и готовую ViewModel.

    На следующих этапах будет постепенно заменён
    реальными запросами PostgreSQL.
    """

    def load(self) -> MarketIntelligenceVM:
        return build_default_market_intelligence_vm()
