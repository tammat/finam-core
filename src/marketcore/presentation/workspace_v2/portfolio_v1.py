from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.presentation.workspace_v2.design_system_v1 import (
    render_action_card,
    render_kpi_card,
    render_kpi_card_v2,
)
from marketcore.presentation.workspace_v2.display_terms_v1 import (
    load_terms,
    term_label,
    term_tooltip,
)


def _safe(value: Any) -> str:
    return escape(str(value if value is not None else "—"))


def _fmt_num(value: Any) -> str:
    try:
        return str(Decimal(str(value or 0)).quantize(Decimal("0.01")))
    except Exception:
        return "—"


def _table_exists(cur, full_name: str) -> bool:
    cur.execute("SELECT to_regclass(%s) IS NOT NULL AS exists_flag", (full_name,))
    return bool(cur.fetchone()["exists_flag"])


def _count_table(cur, full_name: str) -> int:
    if not _table_exists(cur, full_name):
        return 0
    schema_name, table_name = full_name.split(".", 1)
    cur.execute(
        """
        SELECT count(*) AS rows_total
        FROM pg_catalog.pg_class c
        JOIN pg_catalog.pg_namespace n ON n.oid=c.relnamespace
        WHERE n.nspname=%s AND c.relname=%s
        """,
        (schema_name, table_name),
    )
    if int(cur.fetchone()["rows_total"] or 0) != 1:
        return 0
    cur.execute(f'SELECT count(*) AS rows_total FROM "{schema_name}"."{table_name}"')
    return int(cur.fetchone()["rows_total"] or 0)


def render_workspace_v2_portfolio_v1() -> str:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT trades_total, net_pnl_points, profit_factor, expectancy_r
                FROM analytics.paper_execution_summary_v1
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            paper = cur.fetchone() or {}

            cur.execute(
                """
                SELECT count(*) AS feedback_rows
                FROM analytics.paper_execution_feedback_v1
                WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
                """
            )
            feedback_rows = int(cur.fetchone()["feedback_rows"] or 0)

            cur.execute(
                """
                SELECT gate_status
                FROM analytics.marketcore_model_health_gate_v1
                WHERE gate_code='PRODUCTION'
                ORDER BY created_at DESC
                LIMIT 1
                """
            )
            gate = cur.fetchone() or {}
            production_status = str(gate.get("gate_status") or "LOCKED")

            terms = load_terms(
                cur,
                [
                    "PROFIT_FACTOR",
                    "EXPECTANCY_R",
                    "FEEDBACK_QUEUE",
                    "MODE",
                    "PAPER_MODE",
                    "STATUS_WARNING",
                    "STATUS_LOCKED",
                    "STATUS_PASS",
                ],
                mode="short",
            )

            position_rows = 0
            capital_rows = 0
            for table_name in (
                "portfolio.position_v1",
                "portfolio.positions_v1",
                "public.portfolio_position_v1",
                "analytics.portfolio_position_v1",
            ):
                position_rows = max(position_rows, _count_table(cur, table_name))

            for table_name in (
                "portfolio.capital_v1",
                "portfolio.capital_snapshot_v1",
                "public.capital_v1",
                "analytics.capital_snapshot_v1",
            ):
                capital_rows = max(capital_rows, _count_table(cur, table_name))

    return f"""
<link rel="stylesheet" href="/static/workspace_v2_design_system_v1.css">
<main class="mc-v2-shell">
  <section class="mc-v2-card">
    <div class="mc-v2-kpi-label">MarketCore Workspace V2</div>
    <h1>Портфель</h1>
    <div class="mc-v2-badge mc-v2-badge-locked">Production: {_safe(production_status)}</div>
    <p>Рабочая область портфеля: капитал, позиции, PnL, риск и будущий ввод капитала.</p>
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_kpi_card("Позиции", position_rows, "WARNING" if position_rows == 0 else "PASS", "Открытые позиции")}
    {render_kpi_card("Капитал", capital_rows, "WARNING" if capital_rows == 0 else "PASS", "Снимки капитала")}
    {render_kpi_card("Paper PnL", _fmt_num(paper.get("net_pnl_points")), "WARNING", "Бумажный результат")}
    {render_kpi_card("Сделки", paper.get("trades_total", 0), "WARNING", "Paper сделки")}
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_kpi_card_v2(term_label(terms, "PROFIT_FACTOR"), _fmt_num(paper.get("profit_factor")), "WARNING", term_label(terms, "STATUS_WARNING"), term_tooltip(terms, "PROFIT_FACTOR"))}
    {render_kpi_card_v2(term_label(terms, "EXPECTANCY_R"), _fmt_num(paper.get("expectancy_r")), "WARNING", term_label(terms, "STATUS_WARNING"), term_tooltip(terms, "EXPECTANCY_R"))}
    {render_kpi_card_v2(term_label(terms, "FEEDBACK_QUEUE"), feedback_rows, "WARNING", term_label(terms, "STATUS_WARNING"), term_tooltip(terms, "FEEDBACK_QUEUE"))}
    {render_kpi_card_v2(term_label(terms, "MODE"), term_label(terms, "PAPER_MODE"), "WARNING", term_label(terms, "STATUS_WARNING"), term_tooltip(terms, "PAPER_MODE"))}
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_action_card("Доб. капитал", "Будущий безопасный ввод или корректировка капитала с подтверждением.", "Открыть", "/workspace-v2/capital")}
    {render_action_card("Позиции", "Просмотр позиций и экспозиции по режимам Paper / Shadow / Production.", "Открыть", "/workspace-v2/portfolio/positions")}
    {render_action_card("Риск", "Контроль лимитов, просадки и доступного риска.", "Открыть", "/workspace-v2/risk")}
  </section>

  <section class="mc-v2-card" style="margin-top:12px">
    <h2>Правила безопасности</h2>
    <p>Экран портфеля V1 работает только на чтение. Добавление капитала и инструментов будет реализовано отдельными подтверждаемыми действиями.</p>
    <p>runtime_changed=0; execution_changed=0; orders_changed=0; fills_changed=0.</p>
  </section>
</main>
"""


if __name__ == "__main__":
    print(render_workspace_v2_portfolio_v1())
