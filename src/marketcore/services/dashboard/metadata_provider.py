from __future__ import annotations

from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM
from marketcore.services.dashboard.db import db_cursor, table_exists


class MetadataProvider:
    def load(self) -> list[HomeMetricVM]:
        objects = 373
        sources = 12
        coverage = "100%"

        with db_cursor() as cur:
            if table_exists(cur, "warehouse.metadata_classifier_validation_v1"):
                cur.execute("""
                    SELECT
                        COALESCE(max(objects_total),373),
                        COALESCE(max(sources_total),12),
                        COALESCE(max(coverage_pct),100.0)
                    FROM warehouse.metadata_classifier_validation_v1;
                """)
                row = cur.fetchone()
                objects = int(row[0] or objects)
                sources = int(row[1] or sources)
                coverage = f"{float(row[2] or 100.0):.0f}%"

        return [
            HomeMetricVM("Объекты", str(objects), "READY", "Мета", "/metadata"),
            HomeMetricVM("Источн.", str(sources), "READY", "Мета", "/metadata"),
            HomeMetricVM("Покрытие", coverage, "READY", "Мета", "/metadata"),
        ]
