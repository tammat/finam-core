from __future__ import annotations

from datetime import datetime, timezone

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
from marketcore.presentation.workspace_v2.resolver.operator_decision_v2_resolver import OperatorDecisionV2Resolver
import os
import psycopg2
import psycopg2.extras
from marketcore.presentation.workspace_v2.viewmodel.home_v2_viewmodel import HomeV2ViewModel


class HomeV2Presenter:
    def __init__(self) -> None:
        self._status_resolver = HomeStatusResolverV1()
        self._operator_resolver = HomeOperatorDashboardResolverV1()

    def load(self) -> HomeV2ViewModel:
        edge_metric, edge_metric_args = self._edge_metric()
        operating = self._operating_status()
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
                self._profit_card("decision", "home.profit_factory.decision", profit["decision"], profit_status, 1, profit["quality"], v2_message_key=f"home.profit_factory.decision.{str(profit['decision_code']).lower()}"),
                self._profit_card("expected", "home.profit_factory.expected", self._money(profit["expected_profit"]), profit_status, 2, v2_value=profit["expected_profit"], v2_format_code="MONEY_RUB"),
                self._profit_card("realized", "home.profit_factory.realized", self._money(profit["realized_profit"]), profit_status, 3, v2_value=profit["realized_profit"], v2_format_code="MONEY_RUB"),
                self._profit_card("gap", "home.profit_factory.gap", self._money(profit["profit_gap"]), profit_status, 4, v2_value=profit["profit_gap"], v2_format_code="MONEY_RUB"),
                self._profit_card("roi", "home.profit_factory.roi", self._percent(profit["realized_roi"]), profit_status, 5, v2_value=profit["realized_roi"], v2_format_code="PERCENT_RATIO"),
            ),
        )
        operating_section = BaseSection(
            section_id="home.section.operating_traffic",
            section_type=SectionType.OBSERVATION,
            title_key="home.section.status.title",
            subtitle_key="home.section.status.subtitle",
            order=1,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=(
                self._traffic_card("data", "home.card.status.research.title", "home.card.status.pending.subtitle", operating["data"], UiStatusCode.OK if operating["data_ready"] else UiStatusCode.WARNING, "/workspace-v2/control-center/edge-oos/data-quality", 1, "home.traffic.data.value", {"ready": operating["ready"], "total": operating["total"]}),
                self._traffic_card("edge", "home.card.edge.title", "home.card.status.blocked.subtitle", operating["edge"], UiStatusCode.BLOCKED, "/workspace-v2/control-center/edge-oos/relationship-factory", 2, "home.traffic.edge.value", {"passed": operating["passed"]}),
                self._traffic_card("forward", "home.card.status.observation.title", "home.card.status.pending.subtitle", operating["forward"], UiStatusCode.WARNING, "/workspace-v2/control-center/edge-oos/strategy-generator", 3, "home.traffic.forward.value", {"candidates": operating["candidates"], "observations": operating["observations"]}),
                self._traffic_card("execution", "home.card.status.runtime.title", "home.card.status.pending.subtitle", operating["execution"], UiStatusCode.WARNING, "/workspace-v2/control-center/edge-oos/execution-edge", 4, "home.traffic.execution.unverified", {}),
                self._traffic_card("live", "home.card.control_center.title", "home.card.status.blocked.subtitle", "LIVE: продвижение заблокировано", UiStatusCode.BLOCKED, "/workspace-v2/control-center/edge-oos", 5, "home.traffic.live.blocked", {}),
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
        operator_decisions = OperatorDecisionV2Resolver().resolve()
        operator_actions_section = BaseSection(
            section_id="home.operator.actions",
            section_type=SectionType.ACTIONS,
            title_key="home.operator.actions.section.title",
            subtitle_key="home.operator.actions.section.subtitle",
            order=17,
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            cards=tuple(self._operator_action_card(item) for item in operator_decisions),
        )
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
                self._nav_card("home.card.profit", "home.card.profit.title", "/", 5, self._percent(profit["realized_roi"]), v2_value=profit["realized_roi"], v2_format_code="PERCENT_RATIO"),
                self._nav_card("home.card.portfolio", "home.card.portfolio.title", "/workspace-v2/portfolio", 10),
                self._nav_card("home.card.portfolio.tablet", "home.card.portfolio.tablet.title", "/workspace-v2/portfolio/tablet", 14),
                self._nav_card("home.card.portfolio.phone", "home.card.portfolio.phone.title", "/workspace-v2/portfolio/phone", 15),
                self._nav_card("home.card.probe", "home.card.probe.title", "/workspace-v2/probe", 20, available=False),
                self._nav_card("home.card.research", "home.card.research.title", "/workspace-v2/research", 30, available=False),
                self._nav_card("home.card.control_center", "home.card.control_center.title", "/workspace-v2/control-center/edge-oos", 35, edge_metric, v2_message_key="home.control_center.edge_metric", v2_message_args=edge_metric_args),
            ),
        )

        layout = BaseLayout(
            layout_id="home.layout.desktop",
            layout_type=LayoutType.DESKTOP,
            title_key="home.workspace.title",
            subtitle_key="home.workspace.subtitle",
            status_code=UiStatusCode.WARNING,
            status_label_key="ui.status.warning",
            sections=(operating_section, profit_section, system_section, status_section, operator_actions_section, operator_section, navigation_section),
        )

        return HomeV2ViewModel(layout=layout)

    @staticmethod
    def _operator_action_card(item) -> BaseCard:
        blocked = str(item["policy_verdict"]) == "BLOCKED"
        acknowledgeable = not blocked and str(item["selection_status"]) == "NOT_SELECTED"
        measurable = (
            not blocked and str(item["selection_status"]) == "ACKNOWLEDGED"
            and str(item["feedback_status"]) == "PENDING"
            and item["measurement_due_at"] is not None
            and item["measurement_due_at"].astimezone(timezone.utc) <= datetime.now(timezone.utc)
        )
        action_id = "operator.decision.acknowledge" if acknowledgeable else ("operator.decision.measure" if measurable else None)
        command_code = "OPERATOR.ACKNOWLEDGE_DECISION" if acknowledgeable else ("OPERATOR.MEASURE_DECISION" if measurable else None)
        rollback_code = "OPERATOR.CANCEL_PENDING_ACKNOWLEDGEMENT" if acknowledgeable else ("OPERATOR.CANCEL_PENDING_MEASUREMENT" if measurable else None)
        return BaseCard(
            widget_id=f"home.operator.action.{item['rank']}",
            widget_type=WidgetType.STATUS,
            card_type=CardType.DECISION,
            title_key="home.operator.action.title",
            subtitle_key="home.operator.action.subtitle",
            status_code=UiStatusCode.BLOCKED if blocked else UiStatusCode.WARNING,
            status_label_key="ui.status.blocked" if blocked else "ui.status.warning",
            priority=int(item["rank"]),
            actions=({"action_code": action_id, "target": str(item["decision_id"])},) if action_id else (),
            payload={
                "quality": item["quality_code"],
                "updated_at": item["source_as_of"],
                "v2_value": item["action_code"],
                "v2_format_code": "DOMAIN_CODE",
                "operator_decision_id": str(item["decision_id"]),
                "operator_action_expires_at": item["expires_at"],
                "operator_action_enabled": bool(action_id),
                "operator_action_id": action_id,
                "operator_command_code": command_code,
                "operator_rollback_code": rollback_code,
                "operator_fields": (
                    ("home.operator.field.loss_source",item["loss_source_code"],"DOMAIN_CODE"),
                    ("home.operator.field.expected_profit_impact",item["expected_profit_impact"],"MONEY_RUB"),
                    ("home.operator.field.risk_impact",item["risk_impact_code"],"DOMAIN_CODE"),
                    ("home.operator.field.confidence",item["confidence"],"PERCENT_RATIO"),
                    ("home.operator.field.sample_size",item["sample_size"],"INTEGER"),
                    ("home.operator.field.sample_sufficiency",item["sample_sufficiency_code"],"DOMAIN_CODE"),
                    ("home.operator.field.policy_verdict",item["policy_verdict"],"DOMAIN_CODE"),
                    ("home.operator.field.autonomy_mode",item["autonomy_mode"],"DOMAIN_CODE"),
                    ("home.operator.field.expires_at",item["expires_at"],"DATETIME"),
                    ("home.operator.field.rollback",item["rollback_plan_code"],"DOMAIN_CODE"),
                    ("home.operator.field.feedback",item["feedback_status"],"DOMAIN_CODE"),
                    ("home.operator.field.selection",item["selection_status"],"DOMAIN_CODE"),
                    ("home.operator.field.baseline",item["baseline_value"],"DECIMAL"),
                    ("home.operator.field.measurement_due",item["measurement_due_at"],"DATETIME"),
                    ("home.operator.field.actual_result",item["actual_result"],"DECIMAL"),
                ),
            },
        )

    def _profit_card(self, code, title_key, value, status, priority, quality="VERIFIED", *, v2_value=None, v2_format_code=None, v2_message_key=None) -> BaseCard:
        card_status = status if code == "decision" else (UiStatusCode.OK if quality == "VERIFIED" else status)
        return BaseCard(
            widget_id=f"home.profit_factory.{code}", widget_type=WidgetType.KPI,
            card_type=(CardType.DECISION if code == "decision" else CardType.KPI),
            title_key=title_key, subtitle_key="home.profit_factory.verified",
            status_code=card_status, status_label_key=("ui.status.ok" if card_status == UiStatusCode.OK else "ui.status.warning"),
            priority=priority, payload={"primary_value": value, "quality": quality, "v2_value": v2_value, "v2_format_code": v2_format_code, "v2_message_key": v2_message_key},
        )

    @staticmethod
    def _traffic_card(code, title_key, subtitle_key, value, status, target, priority, v2_message_key, v2_message_args) -> BaseCard:
        return BaseCard(
            widget_id=f"home.traffic.{code}", widget_type=WidgetType.STATUS,
            card_type=CardType.ACTION, title_key=title_key,
            subtitle_key=subtitle_key,
            status_code=status,
            status_label_key=("ui.status.ok" if status == UiStatusCode.OK else "ui.status.warning"),
            priority=priority,
            actions=({"action_code": ActionCode.OPEN.value, "target": target},),
            payload={"primary_value": value, "v2_message_key": v2_message_key, "v2_message_args": v2_message_args},
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
        v2_value=None,
        v2_format_code=None,
        v2_message_key=None,
        v2_message_args=None,
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
                "v2_value": v2_value,
                "v2_format_code": v2_format_code,
                "v2_message_key": v2_message_key,
                "v2_message_args": v2_message_args or {},
                "availability": "AVAILABLE" if available else "UNAVAILABLE",
            },
        )

    @staticmethod
    def _edge_metric() -> tuple[str, dict[str, int]]:
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
            ready = int(quality.get("ready") or 0)
            symbols = int(quality.get("symbols") or 0)
            return f"PASS {passed} · DATA {ready}/{symbols}", {"passed": passed, "ready": ready, "total": symbols}
        except Exception:
            return "EDGE STATUS", {"passed": 0, "ready": 0, "total": 0}

    @staticmethod
    def _operating_status() -> dict[str, object]:
        """Only measured facts are exposed on the operator's first screen."""
        fallback = {
            "data": "Данные: статус уточняется",
            "data_ready": False,
            "edge": "OOS edge: статус уточняется",
            "forward": "Forward: статус уточняется",
            "execution": "Исполнение: статус уточняется",
            "ready": 0, "total": 0, "passed": 0, "candidates": 0, "observations": 0,
        }
        try:
            with psycopg2.connect("postgresql:///finam_core") as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                    cur.execute("""SELECT count(*) AS symbols,count(*) FILTER(WHERE factory_status='READY') AS ready
                        FROM analytics.relationship_data_quality_gate_v1 WHERE audit_run_id=(
                        SELECT audit_run_id FROM analytics.relationship_data_quality_gate_v1 ORDER BY created_at DESC LIMIT 1)""")
                    quality = dict(cur.fetchone() or {})
                    cur.execute("""SELECT count(*) FILTER(WHERE verdict_code='OOS_PASS') AS passed
                        FROM analytics.relationship_factory_result_v2 WHERE discovery_run_id=(
                        SELECT discovery_run_id FROM analytics.relationship_factory_result_v2 ORDER BY created_at DESC LIMIT 1)""")
                    edge = dict(cur.fetchone() or {})
                    cur.execute("""SELECT analytics.forward_edge_baseline_cohort_id_v1() AS cohort_id""")
                    cohort = cur.fetchone()
                    forward = {"candidates": 0, "observations": 0}
                    if cohort:
                        cur.execute("""SELECT count(*) candidates FROM analytics.forward_edge_incubator_v1 WHERE cohort_id=%s""", (cohort["cohort_id"],))
                        forward.update(dict(cur.fetchone() or {}))
                        cur.execute("""SELECT count(*) observations FROM analytics.forward_edge_observation_v1 WHERE cohort_id=%s""", (cohort["cohort_id"],))
                        forward.update(dict(cur.fetchone() or {}))
            symbols = int(quality.get("symbols") or 0)
            ready = int(quality.get("ready") or 0)
            return {
                "data": f"Данные: {ready}/{symbols} источников готовы",
                "data_ready": symbols > 0 and ready == symbols,
                "edge": f"OOS edge: подтверждено {int(edge.get('passed') or 0)}",
                "forward": f"Forward: {int(forward.get('candidates') or 0)} кандидатов · {int(forward.get('observations') or 0)} наблюдений",
                "execution": "Исполнение: bid/ask и стакан не подтверждены",
                "ready": ready,
                "total": symbols,
                "passed": int(edge.get("passed") or 0),
                "candidates": int(forward.get("candidates") or 0),
                "observations": int(forward.get("observations") or 0),
            }
        except Exception:
            return fallback
