from __future__ import annotations

from decimal import Decimal
from html import escape
from typing import Any

import psycopg2
import psycopg2.extras

from marketcore.presentation.workspace_v2.design_system_v1 import (
    render_action_card,
    render_kpi_card_v2,
    render_progress,
)
from marketcore.presentation.workspace_v2.display_terms_v1 import (
    load_terms,
    term_label,
    term_tooltip,
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


def _feedback_rows(cur) -> list[dict[str, Any]]:
    cur.execute("""
        SELECT
            f.feedback_reason_code,
            f.feedback_severity_code,
            f.recommended_action_code,
            count(*) AS rows_total,
            coalesce(rr.caption_short, f.feedback_reason_code) AS reason_caption,
            coalesce(ss.caption_short, f.feedback_severity_code) AS severity_caption,
            coalesce(aa.caption_short, f.recommended_action_code) AS action_caption
        FROM analytics.paper_execution_feedback_v1 f
        LEFT JOIN presentation.ui_resource_v1 rr
          ON rr.resource_key='paper.feedback.reason.'||lower(f.feedback_reason_code)
         AND rr.locale_code='ru'
        LEFT JOIN presentation.ui_resource_v1 ss
          ON ss.resource_key='paper.feedback.severity.'||lower(f.feedback_severity_code)
         AND ss.locale_code='ru'
        LEFT JOIN presentation.ui_resource_v1 aa
          ON aa.resource_key='paper.feedback.'||lower(f.recommended_action_code)
         AND aa.locale_code='ru'
        WHERE f.source_version='PAPER_EXECUTION_FEEDBACK_ENGINE_V1'
        GROUP BY
            f.feedback_reason_code,
            f.feedback_severity_code,
            f.recommended_action_code,
            rr.caption_short,
            ss.caption_short,
            aa.caption_short
        ORDER BY rows_total DESC, f.feedback_reason_code
        LIMIT 6
    """)
    return [dict(r) for r in cur.fetchall()]


def render_mission_control_v1() -> str:
    with psycopg2.connect("postgresql:///finam_core") as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            terms = load_terms(
                cur,
                [
                    "WORKSPACE_TITLE",
                    "HOME",
                    "PROJECT_STATE",
                    "RESEARCH_STATE",
                    "READY_STATE",
                    "NEXT_ACTION",
                    "CONTINUE_PAPER",
                    "CHECK_APPROVAL",
                    "MAIN_REASONS",
                    "MARKET_MODEL_QUALITY",
                    "LEARNING_READINESS",
                    "ROBUSTNESS",
                    "PAPER_COVERAGE",
                    "PRODUCTION_READINESS",
                    "TRADES",
                    "PROFIT_FACTOR",
                    "EXPECTANCY_R",
                    "PORTFOLIO",
                    "INSTRUMENTS",
                    "PAPER_MODE",
                    "OPEN_ACTION",
                    "STATUS_WARNING",
                    "STATUS_PASS",
                    "STATUS_LOCKED",
                ],
                mode="short",
            )

            snapshot_id = _latest_model_health_snapshot(cur)
            if snapshot_id is None:
                return render_action_card(
                    term_label(terms, "HOME"),
                    term_tooltip(terms, "PRODUCTION_READINESS"),
                    term_label(terms, "OPEN_ACTION"),
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
            if production_status == "PASS":
                main_state = term_label(terms, "READY_STATE")
                next_action = term_label(terms, "CHECK_APPROVAL")
                status_label = term_label(terms, "STATUS_PASS")
            else:
                main_state = term_label(terms, "RESEARCH_STATE")
                next_action = term_label(terms, "CONTINUE_PAPER")
                status_label = term_label(terms, "STATUS_WARNING")

            feedback_html = "".join(
                "<li>"
                f"<b>{_safe(r['reason_caption'])}</b> "
                f"<span>{_safe(r['severity_caption'])}</span> "
                f"<em>{_safe(r['rows_total'])}</em>"
                "</li>"
                for r in feedback
            ) or f"<li>{_safe(term_tooltip(terms, 'MAIN_REASONS'))}</li>"

            return f"""
<link rel="stylesheet" href="/static/workspace_v2_design_system_v1.css">
<main class="mc-v2-shell">
  <section class="mc-v2-card">
    <div class="mc-v2-kpi-label">{_safe(term_label(terms, "WORKSPACE_TITLE"))}</div>
    <h1>{_safe(term_label(terms, "HOME"))}</h1>
    <div class="mc-v2-badge mc-v2-badge-warning">{_safe(main_state)}</div>
    <p>{_safe(term_label(terms, "PRODUCTION_READINESS"))}: <b>{_safe(production_status)}</b>. {_safe(term_label(terms, "NEXT_ACTION"))}: <b>{_safe(next_action)}</b>.</p>
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_kpi_card_v2(term_label(terms, "MARKET_MODEL_QUALITY"), _fmt_pct(market_quality.get("component_value")), str(market_quality.get("component_status", "")), status_label, term_tooltip(terms, "MARKET_MODEL_QUALITY"))}
    {render_kpi_card_v2(term_label(terms, "LEARNING_READINESS"), _fmt_pct(learning.get("component_value")), str(learning.get("component_status", "")), status_label, term_tooltip(terms, "LEARNING_READINESS"))}
    {render_kpi_card_v2(term_label(terms, "ROBUSTNESS"), _fmt_pct(robustness.get("component_value")), str(robustness.get("component_status", "")), status_label, term_tooltip(terms, "ROBUSTNESS"))}
    {render_kpi_card_v2(term_label(terms, "PAPER_COVERAGE"), _fmt_pct(paper_coverage.get("component_value")), str(paper_coverage.get("component_status", "")), status_label, term_tooltip(terms, "PAPER_COVERAGE"))}
  </section>

  <section class="mc-v2-card" style="margin-top:12px">
    <h2>{_safe(term_label(terms, "LEARNING_READINESS"))}</h2>
    {render_progress(learning.get("component_value", 0), term_label(terms, "LEARNING_READINESS"))}
    <p>{_safe(term_label(terms, "TRADES"))}: <b>{_safe(paper.get("trades_total"))}</b>. {_safe(term_label(terms, "PROFIT_FACTOR"))}: <b>{_safe(paper.get("profit_factor"))}</b>. {_safe(term_label(terms, "EXPECTANCY_R"))}: <b>{_safe(paper.get("expectancy_r"))}</b>.</p>
  </section>

  <section class="mc-v2-card" style="margin-top:12px">
    <h2>{_safe(term_label(terms, "MAIN_REASONS"))}</h2>
    <ul>{feedback_html}</ul>
  </section>

  <section class="mc-v2-grid" style="margin-top:12px">
    {render_action_card(term_label(terms, "PORTFOLIO"), term_tooltip(terms, "PORTFOLIO"), term_label(terms, "OPEN_ACTION"), "/workspace-v2/portfolio")}
    {render_action_card(term_label(terms, "INSTRUMENTS"), term_tooltip(terms, "INSTRUMENTS"), term_label(terms, "OPEN_ACTION"), "/workspace-v2/instruments")}
    {render_action_card(term_label(terms, "PAPER_MODE"), term_tooltip(terms, "PAPER_MODE"), term_label(terms, "OPEN_ACTION"), "/workspace-v2/paper")}
  </section>
</main>
"""


if __name__ == "__main__":
    print(render_mission_control_v1())
