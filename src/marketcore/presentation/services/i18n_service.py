from __future__ import annotations

from marketcore.presentation.api_client import get_json


class I18NService:
    FALLBACK = {
        ("ui", "marketcore_os", "ru"): "MarketCore OS",
        ("ui", "platform_m2", "ru"): "Platform M2",
        ("ui", "knowledge_graph", "ru"): "Граф знаний",
        ("ui", "validation", "ru"): "Валидация",
        ("ui", "statistics", "ru"): "Статистика",
        ("ui", "paper_edge_discovery_center", "ru"): "Центр поиска Edge",
        ("ui", "runtime", "ru"): "Runtime",
        ("ui", "research", "ru"): "Исследования",
        ("ui", "portfolio", "ru"): "Портфель",
        ("ui", "risk", "ru"): "Риск",
    }

    def label(self, object_type: str, object_key: str, locale: str = "ru") -> str:
        fallback = self.FALLBACK.get((object_type, object_key, locale), object_key)

        data = get_json("/api/kg/v1/ontology", timeout=1.0)
        rows = data.get("data") or []

        for row in rows:
            if (
                row.get("object_type") == object_type
                and row.get("object_key") == object_key
                and row.get("locale") == locale
            ):
                return str(row.get("label") or fallback)

        return fallback
