from __future__ import annotations

from decimal import Decimal

from marketcore.presentation.viewmodels.execution_center_vm import (
    ExecutionCenterVM,
    ExecutionFillVM,
    ExecutionMetricVM,
    ExecutionOrderVM,
    build_default_execution_center_vm,
)
from marketcore.services.common.safe_query import safe_query
from marketcore.services.dashboard.db import db_cursor, table_exists


def _ru_decimal(value: object, digits: int = 2) -> str:
    try:
        return f"{Decimal(str(value)):.{digits}f}".replace(".", ",")
    except Exception:
        return "н/д"


class ExecutionCenterService:
    def load(self) -> ExecutionCenterVM:
        return safe_query(self._load_from_db, build_default_execution_center_vm())

    def _load_from_db(self) -> ExecutionCenterVM:
        fallback = build_default_execution_center_vm()

        orders = fallback.orders
        fills = fallback.fills

        with db_cursor() as cur:
            if table_exists(cur, "public.orders"):
                cur.execute("""
                    SELECT
                        COALESCE(created_at::text, 'Сейчас'),
                        COALESCE(symbol, 'н/д'),
                        COALESCE(side, 'н/д'),
                        COALESCE(qty, 0),
                        COALESCE(status, 'READY')
                    FROM public.orders
                    ORDER BY id DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
                if rows:
                    orders = [
                        ExecutionOrderVM(
                            time_label="Сейчас",
                            symbol=str(r[1]),
                            side=str(r[2]),
                            qty=str(r[3]),
                            status=str(r[4]),
                        )
                        for r in rows
                    ]

            if table_exists(cur, "public.fills"):
                cur.execute("""
                    SELECT
                        COALESCE(created_at::text, 'Сейчас'),
                        COALESCE(symbol, 'н/д'),
                        COALESCE(qty, 0),
                        COALESCE(price, 0),
                        COALESCE(status, 'READY')
                    FROM public.fills
                    ORDER BY id DESC
                    LIMIT 5;
                """)
                rows = cur.fetchall()
                if rows:
                    fills = [
                        ExecutionFillVM(
                            time_label="Сейчас",
                            symbol=str(r[1]),
                            qty=str(r[2]),
                            price=_ru_decimal(r[3], 2),
                            status=str(r[4]),
                        )
                        for r in rows
                    ]

        return ExecutionCenterVM(
            title="Выполнение",
            subtitle="Execution Center",
            overview=[
                ExecutionMetricVM("Исполнение", "Выкл.", "DISABLED", "Детали", "/execution"),
                ExecutionMetricVM("Micro Live", "Выкл.", "DISABLED", "Детали", "/execution"),
                ExecutionMetricVM("Заявки", str(len(orders)), "READY", "Детали", "/execution"),
                ExecutionMetricVM("Сделки", str(len(fills)), "READY", "Детали", "/execution"),
            ],
            orders=orders,
            fills=fills,
            actions=fallback.actions,
        )
