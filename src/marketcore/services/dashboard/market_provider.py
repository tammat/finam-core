from __future__ import annotations

from marketcore.presentation.formatters.number_formatter import NumberFormatter
from marketcore.presentation.viewmodels.executive_overview_vm import HomeMetricVM
from marketcore.services.dashboard.db import db_cursor, table_exists


class MarketProvider:
    def load(self) -> list[HomeMetricVM]:
        bars = 0
        ticks = 0
        symbols = 0
        fresh = 0

        with db_cursor() as cur:
            if table_exists(cur, "warehouse.market_data_quality_audit_v1"):
                cur.execute("""
                    SELECT COALESCE(max(rows_checked),0)
                    FROM warehouse.market_data_quality_audit_v1
                    WHERE audit_name='MARKET_DATA_QUALITY_AUDIT_V1'
                      AND object_name='public.market_bars';
                """)
                bars = int(cur.fetchone()[0] or 0)

                cur.execute("""
                    SELECT COALESCE(max(rows_checked),0)
                    FROM warehouse.market_data_quality_audit_v1
                    WHERE audit_name='MARKET_DATA_QUALITY_AUDIT_V1'
                      AND object_name='public.market_ticks';
                """)
                ticks = int(cur.fetchone()[0] or 0)

            if table_exists(cur, "warehouse.market_data_freshness_audit_v1"):
                cur.execute("""
                    SELECT
                        count(*),
                        count(*) FILTER (WHERE freshness_status='FRESH')
                    FROM warehouse.market_data_freshness_audit_v1
                    WHERE audit_name='MARKET_DATA_FRESHNESS_AUDIT_V1'
                      AND object_name='public.market_bars';
                """)
                row = cur.fetchone()
                symbols = int(row[0] or 0)
                fresh = int(row[1] or 0)

        return [
            HomeMetricVM("Бары", NumberFormatter.compact(bars), "READY", "Рынок", "/market"),
            HomeMetricVM("Тики", NumberFormatter.compact(ticks), "READY", "Рынок", "/market"),
            HomeMetricVM("Инстр.", str(symbols), "READY", "Рынок", "/market"),
            HomeMetricVM("Fresh", str(fresh), "READY", "Рынок", "/market"),
        ]
