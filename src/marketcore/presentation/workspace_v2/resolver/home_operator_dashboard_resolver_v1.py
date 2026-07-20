from __future__ import annotations

from typing import Any

import psycopg2
import psycopg2.extras
from psycopg2 import sql

from marketcore.presentation.framework.registry import UiStatusCode
from marketcore.presentation.workspace_v2.domain.home_operator_dashboard_model_v1 import (
    HomeOperatorDashboardItemV1,
)
from marketcore.presentation.workspace_v2.mapper.home_status_mapper_v1 import (
    HomeStatusScalarMapperV1,
)


class HomeOperatorDashboardResolverV1:
    SOURCES = (
        (
            "model_health",
            "home.operator.model_health.title",
            "home.operator.model_health.subtitle",
            ("analytics.marketcore_model_health_snapshot_v1",),
        ),
        (
            "recommendations",
            "home.operator.recommendations.title",
            "home.operator.recommendations.subtitle",
            ("analytics.marketcore_model_health_recommendation_v1", "analytics.recommendation_score_v1"),
        ),
        (
            "edge_search",
            "home.operator.edge_search.title",
            "home.operator.edge_search.subtitle",
            ("analytics.edge_search_cycle_status_v1",),
        ),
        (
            "signal_funnel",
            "home.operator.signal_funnel.title",
            "home.operator.signal_funnel.subtitle",
            ("analytics.signal_funnel_snapshot_v1", "analytics.signal_funnel_reason_snapshot_v1"),
        ),
        ("diagnostic_funnels","home.operator.diagnostic_funnels.title","home.operator.diagnostic_funnels.subtitle",("analytics.edge_diagnostic_funnel_run_v1",)),
        ("main_loss","home.operator.main_loss.title","home.operator.main_loss.subtitle",("analytics.edge_validation_funnel_analysis_v1","analytics.signal_funnel_snapshot_v1")),
        ("loss_solution","home.operator.loss_solution.title","home.operator.loss_solution.subtitle",("analytics.edge_validation_funnel_remediation_v1",)),
        (
            "risk",
            "home.operator.risk.title",
            "home.operator.risk.subtitle",
            ("analytics.risk_decision_snapshot_v1", "public.risk_event_audit_v1"),
        ),
        (
            "events",
            "home.operator.events.title",
            "home.operator.events.subtitle",
            ("public.event_store", "public.events", "public.execution_events"),
        ),
    )

    def __init__(self) -> None:
        self._cache: tuple[HomeOperatorDashboardItemV1, ...] | None = None

    def resolve(self) -> tuple[HomeOperatorDashboardItemV1, ...]:
        if self._cache is not None:
            return self._cache

        with psycopg2.connect("postgresql:///finam_core") as conn:
            with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
                items = tuple(
                    self._item(cur, item_code, title_key, subtitle_key, table_names)
                    for item_code, title_key, subtitle_key, table_names in self.SOURCES
                )

        self._cache = items
        return items

    def _item(
        self,
        cur: Any,
        item_code: str,
        title_key: str,
        subtitle_key: str,
        table_names: tuple[str, ...],
    ) -> HomeOperatorDashboardItemV1:
        if item_code == "edge_search":
            return self._edge_search_item(cur, item_code, title_key, subtitle_key)
        if item_code == "model_health":
            return self._model_health_item(cur, item_code, title_key, subtitle_key)
        if item_code == "signal_funnel":
            return self._signal_funnel_item(cur, item_code, title_key, subtitle_key)
        if item_code == "diagnostic_funnels":
            return self._diagnostic_funnels_item(cur,item_code,title_key,subtitle_key)
        if item_code in ("main_loss","loss_solution"):
            return self._loss_item(cur,item_code,title_key,subtitle_key)
        rows_total = sum(self._safe_count(cur, table_name) for table_name in table_names)
        status_code = UiStatusCode.OK if rows_total > 0 else UiStatusCode.WARNING

        return HomeOperatorDashboardItemV1(
            item_code=item_code,
            title_key=title_key,
            subtitle_key=subtitle_key,
            status_code=status_code,
            status_label_key=self._status_label_key(status_code),
            rows_total=rows_total,
            updated_at=self._updated_at(cur, table_names),
        )

    def _edge_search_item(self, cur: Any, item_code: str, title_key: str, subtitle_key: str) -> HomeOperatorDashboardItemV1:
        cur.execute("""
            SELECT status_code,current_step,progress_pct,combinations_evaluated,oos_pass,
                   coalesce(finished_at,updated_at) AS displayed_at
            FROM analytics.edge_search_cycle_status_v1
            ORDER BY started_at DESC LIMIT 1
        """)
        row = cur.fetchone() or {}
        status = str(row.get("status_code") or "NOT_RUN")
        stage = str(row.get("current_step") or "NOT_RUN")
        status_ru = {
            "RUNNING": "В работе", "PASS_FOUND": "Есть PASS", "NO_PASS": "Без PASS",
            "FAILED": "Ошибка", "SKIPPED": "Продолжится", "NOT_RUN": "Не запускался",
        }.get(status, status)
        stage_ru = {
            "STARTING": "Запуск", "SYNC_CONTRACT_SPECS": "Спецификации",
            "AUDIT_PNL_UNITS": "Проверка P&L", "RESOLVE_FUTURES_ROLL": "Контракты",
            "SYNC_ECONOMIC_HYPOTHESES": "Гипотезы", "DISCOVER_REGIME": "Режимы",
            "WALKFORWARD": "Проверка", "GOVERN_EXPERIMENTS": "Статистика",
            "METHODOLOGY_GATE": "Методология", "PROMOTE_OOS": "OOS",
            "COMPLETE": "Завершено", "NOT_RUN": "Нет цикла",
        }.get(stage, stage.replace("_", " ").title())
        status_code = UiStatusCode.OK if status == "PASS_FOUND" else UiStatusCode.WARNING
        return HomeOperatorDashboardItemV1(
            item_code=item_code,title_key=title_key,subtitle_key=subtitle_key,
            status_code=status_code,status_label_key=self._status_label_key(status_code),
            rows_total=int(row.get("combinations_evaluated") or 0),
            updated_at=str(row.get("displayed_at") or ""),
            summary_message_key="home.operator.edge_search.summary",
            summary_message_args={
                "status": status_ru,
                "stage": stage_ru,
                "progress": int(row.get("progress_pct") or 0),
                "variants": int(row.get("combinations_evaluated") or 0),
                "passes": int(row.get("oos_pass") or 0),
            },
        )

    def _model_health_item(self, cur: Any, item_code: str, title_key: str, subtitle_key: str) -> HomeOperatorDashboardItemV1:
        cur.execute("""SELECT model_health_snapshot_id,1 checks,created_at updated_at
            FROM analytics.marketcore_model_health_snapshot_v1 ORDER BY created_at DESC LIMIT 1""")
        row = cur.fetchone() or {}
        cur.execute("""SELECT count(*) recommendations
            FROM analytics.marketcore_model_health_recommendation_v1
            WHERE model_health_snapshot_id=%s""",(row.get("model_health_snapshot_id") or -1,))
        recommendations = int((cur.fetchone() or {}).get("recommendations") or 0)
        checks = int(row.get("checks") or 0)
        status = UiStatusCode.OK if checks and not recommendations else UiStatusCode.WARNING
        return HomeOperatorDashboardItemV1(
            item_code=item_code,title_key=title_key,subtitle_key=subtitle_key,
            status_code=status,status_label_key=self._status_label_key(status),rows_total=checks,
            updated_at=str(row.get("updated_at") or ""),summary_message_key="home.operator.model_health.summary",
            summary_message_args={"checks":checks,"recommendations":recommendations},
        )

    def _signal_funnel_item(self, cur: Any, item_code: str, title_key: str, subtitle_key: str) -> HomeOperatorDashboardItemV1:
        cur.execute("""WITH latest AS (
              SELECT max(signal_funnel_snapshot_id) snapshot_id FROM analytics.signal_funnel_snapshot_v1)
            SELECT max(stage_count) FILTER(WHERE stage_code='SIGNALS') signals,
                   max(stage_count) FILTER(WHERE stage_code='ORDERS') orders,
                   max(stage_count) FILTER(WHERE stage_code='TRADES') trades,
                   max(pass_rate_pct) FILTER(WHERE stage_code='ORDERS') conversion,
                   max(created_at) updated_at
            FROM analytics.signal_funnel_stage_v1
            WHERE signal_funnel_snapshot_id=(SELECT snapshot_id FROM latest)""")
        row = cur.fetchone() or {}
        signals,orders,trades = (int(row.get(code) or 0) for code in ("signals","orders","trades"))
        status = UiStatusCode.OK if signals and trades else UiStatusCode.WARNING
        return HomeOperatorDashboardItemV1(
            item_code=item_code,title_key=title_key,subtitle_key=subtitle_key,
            status_code=status,status_label_key=self._status_label_key(status),rows_total=signals,
            updated_at=str(row.get("updated_at") or ""),summary_message_key="home.operator.signal_funnel.summary",
            summary_message_args={"signals":signals,"orders":orders,"trades":trades,
                                  "conversion":round(float(row.get("conversion") or 0),1)},
        )

    def _loss_item(self,cur: Any,item_code: str,title_key: str,subtitle_key: str) -> HomeOperatorDashboardItemV1:
        cur.execute("""SELECT bottleneck_stage,lost_variants,recommendation_code,created_at
            FROM analytics.edge_validation_funnel_analysis_v1 ORDER BY created_at DESC LIMIT 1""")
        row=cur.fetchone()
        if not row:
            cur.execute("""WITH latest AS (SELECT signal_funnel_snapshot_id FROM analytics.signal_funnel_snapshot_v1 ORDER BY created_at DESC LIMIT 1),
              losses AS (SELECT stage_code,stage_name,greatest(coalesce(previous_stage_count,stage_count)-stage_count,0) lost,created_at
                FROM analytics.signal_funnel_stage_v1 WHERE signal_funnel_snapshot_id=(SELECT signal_funnel_snapshot_id FROM latest))
              SELECT stage_code AS bottleneck_stage,lost AS lost_variants,'REVIEW_ADMISSION_FILTERS' recommendation_code,created_at
              FROM losses ORDER BY lost DESC LIMIT 1""")
            row=cur.fetchone() or {}
        stage_map={"IN_SAMPLE":"Обучение","OOS":"OOS","AFTER_COSTS":"Издержки","STABILITY":"Устойчивость","ORDERS":"Допуск заявок"}
        solution_map={"REFRAME_ENTRY":"Новые условия входа","REDUCE_OVERFIT":"Снизить переобучение","REDUCE_TURNOVER":"Снизить оборот","EXPAND_EVIDENCE":"Расширить выборку","REVIEW_ADMISSION_FILTERS":"Проверить фильтры допуска"}
        stage=stage_map.get(str(row.get("bottleneck_stage") or ""),str(row.get("bottleneck_stage") or "Нет данных"))
        solution=solution_map.get(str(row.get("recommendation_code") or ""),"Дождаться анализа")
        lost=int(row.get("lost_variants") or 0)
        return HomeOperatorDashboardItemV1(item_code=item_code,title_key=title_key,subtitle_key=subtitle_key,
            status_code=UiStatusCode.WARNING,status_label_key=self._status_label_key(UiStatusCode.WARNING),
            rows_total=lost,updated_at=str(row.get("created_at") or ""),
            summary_message_key="home.operator.main_loss.summary" if item_code=="main_loss" else "home.operator.loss_solution.summary",
            summary_message_args={"stage":stage,"lost":lost,"solution":solution})

    def _diagnostic_funnels_item(self,cur: Any,item_code: str,title_key: str,subtitle_key: str) -> HomeOperatorDashboardItemV1:
        cur.execute("""WITH latest AS (SELECT search_run_id FROM analytics.edge_diagnostic_funnel_run_v1 ORDER BY created_at DESC LIMIT 1)
            SELECT count(*) funnels,count(*) FILTER(WHERE status_code='PASS') passed,
              coalesce((array_agg(d.title_ru ORDER BY r.lost_count DESC,d.display_order))[1],'Нет данных') bottleneck,
              coalesce(max(r.lost_count),0) lost,max(r.created_at) updated_at
            FROM analytics.edge_diagnostic_funnel_run_v1 r
            JOIN analytics.edge_diagnostic_funnel_definition_v1 d USING(funnel_code)
            WHERE r.search_run_id=(SELECT search_run_id FROM latest)""")
        row=cur.fetchone() or {}
        funnels=int(row.get("funnels") or 0); passed=int(row.get("passed") or 0)
        status=UiStatusCode.OK if funnels and passed==funnels else UiStatusCode.WARNING
        bottleneck=(str(row.get("bottleneck") or "Нет данных") if funnels else "Ожидается walk-forward")
        return HomeOperatorDashboardItemV1(item_code=item_code,title_key=title_key,subtitle_key=subtitle_key,
            status_code=status,status_label_key=self._status_label_key(status),rows_total=funnels,
            updated_at=str(row.get("updated_at") or ""),summary_message_key="home.operator.diagnostic_funnels.summary",
            summary_message_args={"funnels":funnels,"passed":passed,"bottleneck":bottleneck,"lost":int(row.get("lost") or 0)})

    def _updated_at(
        self,
        cur: Any,
        table_names: tuple[str, ...],
    ) -> str:
        for table_name in table_names:
            if not self._table_exists(cur, table_name):
                continue

            schema_name, object_name = table_name.split(".", 1)

            cur.execute(
                """
                SELECT pg_stat_get_last_analyze_time(c.oid) AS ts
                FROM pg_class c
                JOIN pg_namespace n
                  ON n.oid = c.relnamespace
                WHERE n.nspname = %s
                  AND c.relname = %s
                """,
                (schema_name, object_name),
            )

            row = cur.fetchone()
            if row and row["ts"]:
                return str(row["ts"])

        return ""

    def _safe_count(self, cur: Any, table_name: str) -> int:
        if not self._table_exists(cur, table_name):
            return 0

        schema_name, object_name = table_name.split(".", 1)

        cur.execute(
            sql.SQL("SELECT count(*) AS rows_total FROM {}.{}").format(
                sql.Identifier(schema_name),
                sql.Identifier(object_name),
            )
        )
        row = cur.fetchone()
        return HomeStatusScalarMapperV1.int_value(row, "rows_total")

    def _table_exists(self, cur: Any, table_name: str) -> bool:
        cur.execute("SELECT to_regclass(%s) IS NOT NULL AS ok", (table_name,))
        row = cur.fetchone()
        return HomeStatusScalarMapperV1.bool_value(row, "ok")

    @staticmethod
    def _status_label_key(status_code: UiStatusCode) -> str:
        if status_code == UiStatusCode.OK:
            return "ui.status.ok"
        return "ui.status.warning"
