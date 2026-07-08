from __future__ import annotations

from decimal import Decimal

import psycopg2
import psycopg2.extras

from marketcore.presentation.viewmodels.trading_plan_viewmodel import TradingPlanWidgetViewModel
from marketcore.presentation.widgets.contracts import WidgetViewModel


def _fmt(value: object) -> str:
    if value is None:
        return "—"
    try:
        d = Decimal(str(value))
        return format(d.normalize(), "f")
    except Exception:
        return str(value)


class TradingPlanWidgetProvider:
    def load(self) -> WidgetViewModel:
        vm = self._load_view_model()

        return WidgetViewModel(
            widget_id=vm.widget_id,
            title_key=vm.title_key,
            icon="🧭",
            priority=30,
            category="trading_plan",
            state=vm.state,
            content={
                "trading_plan.direction": self._caption(vm.direction_key),
                "trading_plan.entry_price": vm.entry_price,
                "trading_plan.invalidation_price": vm.stop_price,
                "trading_plan.target_price": vm.target_price,
                "trading_plan.horizon_bars": vm.horizon_bars,
                "trading_plan.risk_unit": vm.risk_unit,
                "trading_plan.profile": self._caption(
                    "trading_plan.profile." + vm.profile_code.replace("PROFILE_", "").lower()
                ) if vm.profile_code.startswith("PROFILE_") else vm.profile_code,
                "trading_plan.entry_source": self._caption(vm.entry_source_key),
                "trading_plan.stop_source": self._caption(vm.stop_source_key),
                "trading_plan.target_source": self._caption(vm.target_source_key),
            },
        )

    def _caption(self, resource_key: str) -> str:
        if not resource_key or resource_key == "—":
            return "—"

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor() as cur:
                cur.execute(
                    '''
                    SELECT caption
                    FROM presentation.ui_resource_v1
                    WHERE resource_key=%s
                      AND locale_code='ru'
                    LIMIT 1
                    ''',
                    (resource_key,),
                )
                row = cur.fetchone()

        return str(row[0]) if row else resource_key

    def _load_view_model(self) -> TradingPlanWidgetViewModel:
        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                cur.execute("""
                    SELECT
                        direction_code,
                        entry_price,
                        invalidation_price,
                        target_price,
                        horizon_bars,
                        risk_unit,
                        evidence_json,
                        created_at
                    FROM knowledge.recommendation_execution_context_v1
                    WHERE source_version='TRADING_PLAN_PARAMETER_BUILDER_V1'
                    ORDER BY created_at DESC
                    LIMIT 1
                """)
                row = cur.fetchone()

        if not row:
            return TradingPlanWidgetViewModel(
                widget_id="trading_plan",
                title_key="widget.trading_plan.title",
                direction_key="trading_plan.direction.direction_neutral",
                entry_price="—",
                stop_price="—",
                target_price="—",
                horizon_bars="—",
                risk_unit="—",
                profile_code="—",
                entry_source_key="—",
                stop_source_key="—",
                target_source_key="—",
                state="readonly",
            )

        evidence = dict(row["evidence_json"] or {})
        entry_source = str(evidence.get("entry_source", ""))
        stop_source = str(evidence.get("stop_source", ""))
        target_source = str(evidence.get("target_source", ""))

        return TradingPlanWidgetViewModel(
            widget_id="trading_plan",
            title_key="widget.trading_plan.title",
            direction_key="trading_plan.direction." + str(row["direction_code"]).lower(),
            entry_price=_fmt(row["entry_price"]),
            stop_price=_fmt(row["invalidation_price"]),
            target_price=_fmt(row["target_price"]),
            horizon_bars=str(row["horizon_bars"]),
            risk_unit=_fmt(row["risk_unit"]),
            profile_code=str(evidence.get("profile_code", "—")),
            entry_source_key="trading_plan.source." + entry_source.lower() if entry_source else "—",
            stop_source_key="trading_plan.source." + stop_source.lower() if stop_source else "—",
            target_source_key="trading_plan.source." + target_source.lower() if target_source else "—",
            state="readonly",
        )
