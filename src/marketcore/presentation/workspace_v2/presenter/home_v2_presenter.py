from __future__ import annotations

from marketcore.presentation.framework.base_card import BaseCard
from marketcore.presentation.framework.base_layout import BaseLayout
from marketcore.presentation.framework.base_section import BaseSection
from marketcore.presentation.framework.registry import (
    ActionCode,
    CardType,
    LayoutType,
    SectionType,
    UiStatusCode,
    WidgetType,
)
from marketcore.presentation.workspace_v2.resolver.home_status_resolver_v1 import (
    HomeStatusResolverV1,
)
from marketcore.presentation.workspace_v2.resolver.home_operator_dashboard_resolver_v1 import (
    HomeOperatorDashboardResolverV1,
)
from marketcore.presentation.workspace_v2.resolver.profit_factory_control_center_resolver_v1 import (
    ProfitFactoryControlCenterResolverV1,
)
import os
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


class HomeV2Presenter:
    def __init__(self) -> None:
        self._status_resolver = HomeStatusResolverV1()
        self._operator_resolver = HomeOperatorDashboardResolverV1()

    def load(self) -> HomeV2ViewModel:
        edge_metric = self._edge_metric()
        profit = ProfitFactoryControlCenterResolverV1(
            scope=os.getenv("MARKETCORE_PROFIT_SCOPE", "REAL")
        ).resolve()
        profit_status = (
            UiStatusCode.OK if profit["status"] == "OK" else UiStatusCode.WARNING
        )
        profit_section = BaseSection(
            section_id="home.profit_factory.control_center",
            section_type=SectionType.SUMMARY,
            title_key="home.profit_factory.title",
            subtitle_key="home.profit_factory.subtitle",
            order=5,
            status_code=profit_status,
            status_label_key=("ui.status.ok" if profit_status == UiStatusCode.OK else "ui.status.warning"),
            cards=(
                self._profit_card("decision", "home.profit_factory.decision", profit["decision"], profit_status, 1, profit["quality"]),
                self._profit_card("expected", "home.profit_factory.expected", self._money(profit["expected_profit"]), profit_status, 2),
                self._profit_card("realized", "home.profit_factory.realized", self._money(profit["realized_profit"]), profit_status, 3),
                self._profit_card("gap", "home.profit_factory.gap", self._money(profit["profit_gap"]), profit_status, 4),
                self._profit_card("roi", "home.profit_factory.roi", self._percent(profit["realized_roi"]), profit_status, 5),
            ),
        )
        system_section = BaseSection(
            section_id="home.section.system",
            section_type=SectionType.SUMMARY,
            title_key="home.section.system.title",
            subtitle_key="home.section.system.subtitle",
            order=10,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=(
                BaseCard(
                    widget_id="home.card.system.status",
                    widget_type=WidgetType.BASE,
                    card_type=CardType.KPI,
                    title_key="home.card.system.status.title",
                    subtitle_key="home.card.system.status.subtitle",
                    status_code=UiStatusCode.WARNING,
                    status_label_key="ui.status.warning",
                    priority=10,
                ),
            ),
        )

        status_items = self._status_resolver.resolve()
        status_section = BaseSection(
            section_id="home.section.status",
            section_type=SectionType.SUMMARY,
            title_key="home.section.status.title",
            subtitle_key="home.section.status.subtitle",
            order=15,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=tuple(
                self._status_card(item, index)
                for index, item in enumerate(status_items, start=1)
            ),
        )

        operator_items = self._operator_resolver.resolve()
        operator_section = BaseSection(
            section_id="home.operator.section",
            section_type=SectionType.SUMMARY,
            title_key="home.operator.section.title",
            subtitle_key="home.operator.section.subtitle",
            order=18,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=tuple(
                self._operator_card(item, index)
                for index, item in enumerate(operator_items, start=1)
            ),
        )

        navigation_section = BaseSection(
            section_id="home.section.navigation",
            section_type=SectionType.ACTIONS,
            title_key="home.section.navigation.title",
            subtitle_key="home.section.navigation.subtitle",
            order=20,
            status_code=UiStatusCode.OK,
            status_label_key="ui.status.ok",
            cards=(
                self._nav_card("home.card.profit", "home.card.profit.title", "/", 5, self._percent(profit["realized_roi"])),
                self._nav_card("home.card.portfolio", "home.card.portfolio.title", "/workspace-v2/portfolio", 10),
                self._nav_card("home.card.portfolio.tablet", "home.card.portfolio.tablet.title", "/workspace-v2/portfolio/tablet", 14),
                self._nav_card("home.card.portfolio.phone", "home.card.portfolio.phone.title", "/workspace-v2/portfolio/phone", 15),
                self._nav_card("home.card.probe", "home.card.probe.title", "/workspace-v2/probe", 20, available=False),
                self._nav_card("home.card.research", "home.card.research.title", "/workspace-v2/research", 30, available=False),
                self._nav_card("home.card.edge", "home.card.edge.title", "/workspace-v2/control-center/edge-oos", 35, edge_metric),
                self._nav_card("home.card.runtime", "home.card.runtime.title", "/runtime", 40, available=False),
            ),
        )

        layout = BaseLayout(
            layout_id="home.layout.desktop",
            layout_type=LayoutType.DESKTOP,
            title_key="home.workspace.title",
            subtitle_key="home.workspace.subtitle",
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            sections=(profit_section, system_section, status_section, operator_section, navigation_section),
        )

        return HomeV2ViewModel(layout=layout)

    def _profit_card(self, code, title_key, value, status, priority, quality="VERIFIED") -> BaseCard:
        return BaseCard(
            widget_id=f"home.profit_factory.{code}", widget_type=WidgetType.KPI,
            card_type=(CardType.DECISION if code == "decision" else CardType.KPI),
            title_key=title_key, subtitle_key="home.profit_factory.verified",
            status_code=status, status_label_key=("ui.status.ok" if status == UiStatusCode.OK else "ui.status.warning"),
            priority=priority, payload={"primary_value": value, "quality": quality},
        )

    @staticmethod
    def _money(value) -> str:
        return f"{value:,.0f} ₽".replace(",", " ")

    @staticmethod
    def _percent(value) -> str:
        return f"{value * 100:.1f}%"

    def _status_card(
        self,
        item,
        priority: int,
    ) -> BaseCard:
        return BaseCard(
            widget_id=f"home.card.status.{item.item_code}",
            widget_type=WidgetType.BASE,
            card_type=CardType.KPI,
            title_key=item.title_key,
            subtitle_key=item.subtitle_key,
            status_code=item.status_code,
            status_label_key=item.status_label_key,
            priority=priority,
            payload={
                "rows_total": item.rows_total,
                "updated_at": item.updated_at,
            },
        )

    def _operator_card(
        self,
        item,
        priority: int,
    ) -> BaseCard:
        return BaseCard(
            widget_id=f"home.operator.{item.item_code}",
            widget_type=WidgetType.BASE,
            card_type=CardType.KPI,
            title_key=item.title_key,
            subtitle_key=item.subtitle_key,
            status_code=item.status_code,
            status_label_key=item.status_label_key,
            priority=priority,
            payload={
                "rows_total": item.rows_total,
                "updated_at": item.updated_at,
            },
        )

    def _nav_card(
        self,
        widget_id: str,
        title_key: str,
        target: str,
        priority: int,
        metric: str = "",
        available: bool = True,
    ) -> BaseCard:
        return BaseCard(
            widget_id=widget_id,
            widget_type=WidgetType.BASE,
            card_type=CardType.ACTION,
            title_key=title_key,
            subtitle_key="ui.action.open",
            status_code=UiStatusCode.OK if available else UiStatusCode.WARNING,
            status_label_key="ui.status.ok" if available else "ui.status.warning",
            priority=priority,
            actions=((
                {"action_code": ActionCode.OPEN.value, "target": target},
            ) if available else ()),
            payload={
                **({"primary_value": metric} if metric else {}),
                "availability": "AVAILABLE" if available else "UNAVAILABLE",
            },
        )

    @staticmethod
    def _edge_metric() -> str:
        try:
            with psycopg2.connect("postgresql:///finam_core") as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""SELECT count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed
                        FROM analytics.relationship_factory_result_v2 WHERE discovery_run_id=(
                            SELECT discovery_run_id FROM analytics.relationship_factory_result_v2 ORDER BY created_at DESC LIMIT 1)""")
                    passed = int((cur.fetchone() or {}).get("passed") or 0)
                    cur.execute("""SELECT count(*) AS symbols,count(*) FILTER(WHERE factory_status='READY') AS ready
                        FROM analytics.relationship_data_quality_gate_v1 WHERE audit_run_id=(
                            SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1)""")
                    quality = dict(cur.fetchone() or {})
            return f"PASS {passed} · DATA {int(quality.get('ready') or 0)}/{int(quality.get('symbols') or 0)}"
        except Exception:
            return "EDGE STATUS"
