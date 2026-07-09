from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.presentation.workspace_v2.design_system_v1 import (
    render_kpi_card,
    render_progress,
    render_action_card,
)


def _safe(value: Any) -> str:
    return escape(str(value if value is not None else "—"))


def _fmt_pct(value: Any) -> str:
    try:
        return f"{Decimal(str(value or 0)).quantize(Decimal('0.01'))}%"
    except Exception:
        return "—"


def _latest_model_health_snapshot(cur) -> int | None:
    cur.execute("""
        SELECT model_health_snapshot_id
        FROM analytics.marketcore_model_health_snapshot_v1
        WHERE source_version='MARKETCORE_MODEL_HEALTH_ENGINE_V1'
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    return int(row["model_health_snapshot_id"]) if row else None


def _component_map(cur, snapshot_id: int) -> dict[str, dict[str, Any]]:
    cur.execute("""
        SELECT component_code, component_value, component_status
        FROM analytics.marketcore_model_health_component_v1
        WHERE model_health_snapshot_id=%s
    """, (snapshot_id,))
    return {str(r["component_code"]): dict(r) for r in cur.fetchall()}


def _feedback_rows(cur) -> list[dict[str, Any]]:
    cur.execute("""
        SELECT feedback_reason_code, feedback_severity_code,
               recommended_action_code, count(*) AS rows_total
        FROM analytics.paper_execution_feedback_v1
        WHERE source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
        GROUP BY feedback_reason_code, feedback_severity_code, recommended_action_code
        ORDER BY rows_total DESC, feedback_reason_code
        LIMIT 6
    """)
    return [dict(r) for r in cur.fetchall()]


def _paper_summary(cur) -> dict[str, Any]:
    cur.execute("""
        SELECT trades_total, profit_factor, expectancy_r, win_rate
        FROM analytics.paper_execution_summary_v1
        ORDER BY created_at DESC
        LIMIT 1
    """)
    row = cur.fetchone()
    return dict(row) if row else {}


def _production_gate(cur, snapshot_id: int) -> dict[str, Any]:
    cur.execute("""
        SELECT gate_status, gate_reason
        FROM analytics.marketcore_model_health_gate_v1
        WHERE model_health_snapshot_id=%s
          AND gate_code='PRODUCTION'
        LIMIT 1
    """, (snapshot_id,))
    row = cur.fetchone()
    return dict(row) if row else {"gate_status": "LOCKED", "gate_reason": "NO_GATE"}


def _term(cur, term_code: str, mode: str = "short") -> str:
    column = {
        "full": "caption_full",
        "short": "caption_short",
        "mobile": "caption_mobile",
    }.get(mode, "caption_short")
    cur.execute(f"""
        SELECT {column} AS caption
        FROM presentation.workspace_v2_display_term_v1
        WHERE term_code=%s
          AND enabled
        LIMIT 1
    """, (term_code,))
    row = cur.fetchone()
    return str(row["caption"]) if row else term_code


def render_mission_control_v1() -> str:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            snapshot_id = _latest_model_health_snapshot(cur)
            if snapshot_id is None:
                return render_action_card(
                    "Центр управления",
                    "Нет снимка здоровья модели. Сначала выполните MARKETCORE_MODEL_HEALTH_ENGINE_V1.",
                    "Открыть диагностику",
                    "/runtime",
                )

            components = _component_map(cur, snapshot_id)
            feedback = _feedback_rows(cur)
            paper = _paper_summary(cur)
            production = _production_gate(cur, snapshot_id)

            learning = components.get("LEARNING_READINESS", {})
            robustness = components.get("ROBUSTNESS", {})
            market_quality = components.get("MARKET_MODEL_QUALITY", {})
            paper_coverage = components.get("PAPER_COVERAGE", {})

            production_status = str(production.get("gate_status", "LOCKED"))
            main_state = "Исследование" if production_status != "PASS" else "Готово"
            next_action = "Продолжать бумажную проверку" if production_status != "PASS" else "Проверить допуск"

            feedback_html = "".join(
                "<li>"
                f"<b>{_safe(r['feedback_reason_code'])}</b> "
                f"<span>{_safe(r['feedback_severity_code'])}</span> "
                f"<em>{_safe(r['rows_total'])}</em>"
                "</li>"
                for r in feedback
            ) or "<li>Нет активных рекомендаций</li>"

            return f"""
<link rel="stylesheet" href="/static/workspace_v2_design_system_v1.css">
<main class="mc-v2-shell">
  <section class="mc-v2-card">
    <div class="mc-v2-kpi-label">MarketCore Workspace V2</div>
    <h1>Центр управления</h1>
    <div class="mc-v2-badge mc-v2-badge-warning">{_safe(main_state)}</div>
    <p>Production: <b>{_safe(production_status)}</b>. Далее: <b>{_safe(next_action)}</b>.</p>
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_kpi_card(_term(cur, "MARKET_MODEL_QUALITY", "short"), _fmt_pct(market_quality.get("component_value")), str(market_quality.get("component_status", "")), "Качество модели")}
    {render_kpi_card(_term(cur, "LEARNING_READINESS", "short"), _fmt_pct(learning.get("component_value")), str(learning.get("component_status", "")), "Готовность к обучению")}
    {render_kpi_card(_term(cur, "ROBUSTNESS", "short"), _fmt_pct(robustness.get("component_value")), str(robustness.get("component_status", "")), "Защита от переобучения")}
    {render_kpi_card(_term(cur, "PAPER_COVERAGE", "short"), _fmt_pct(paper_coverage.get("component_value")), str(paper_coverage.get("component_status", "")), "Бумажная проверка")}
  </section>

  <section class="mc-v2-card" style="margin-top:12px">
    <h2>Готовн.</h2>
    {render_progress(learning.get("component_value", 0), "Готовность к обучению")}
    <p>Сделки: <b>{_safe(paper.get("trades_total"))}</b>. PF: <b>{_safe(paper.get("profit_factor"))}</b>. Ожид.: <b>{_safe(paper.get("expectancy_r"))}</b>.</p>
  </section>

  <section class="mc-v2-card" style="margin-top:12px">
    <h2>Главные причины</h2>
    <ul>{feedback_html}</ul>
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_action_card("Портфель", "Капитал, позиции, риск и PnL.", "Открыть", "/workspace-v2/portfolio")}
    {render_action_card("Инструменты", "Поиск и добавление новых инструментов.", "Открыть", "/workspace-v2/instruments")}
    {render_action_card("Бумага", "Paper Simulation, аналитика, устойчивость.", "Открыть", "/workspace-v2/paper")}
  </section>
</main>
"""


if __name__ == "__main__":
    print(render_mission_control_v1())
