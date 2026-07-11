from __future__ import annotations

from decimal import Decimal
from typing import Any

from marketcore.services.profit_factory_kpi_service_v1 import ProfitFactoryKpiServiceV1


class ProfitFactoryControlCenterResolverV1:
    def __init__(self, *, scope: str = "REAL") -> None:
        self._scope = scope
        self._service = ProfitFactoryKpiServiceV1()

    def resolve(self) -> dict[str, Any]:
        summary = self._service.summary(scope=self._scope)
        eligible = int(summary["eligible_candidates"] or 0)
        expected = self._number(summary["expected_profit"])
        realized = self._number(summary["realized_profit"])
        gap = self._number(summary["profit_gap"])
        realized_roi = self._number(summary["realized_roi"])

        if eligible == 0:
            decision = "Нет подтверждённых данных — проверить цепочку доверия"
            status = "WARNING"
            quality = "NO_VERIFIED_KPI"
        elif realized >= expected:
            decision = "Цель выполнена — оценить увеличение капитала"
            status = "OK"
            quality = "VERIFIED"
        else:
            decision = "Прибыль ниже ожидания — исследовать разрыв"
            status = "WARNING"
            quality = "VERIFIED"

        return {
            **summary,
            "eligible_candidates": eligible,
            "expected_profit": expected,
            "realized_profit": realized,
            "profit_gap": gap,
            "realized_roi": realized_roi,
            "decision": decision,
            "status": status,
            "quality": quality,
        }

    @staticmethod
    def _number(value: Any) -> Decimal:
        return Decimal(str(value or 0))
