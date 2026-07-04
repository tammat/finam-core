from __future__ import annotations

import html
import json
import urllib.request
from typing import Any

from marketcore.presentation.pages.base_page import BaseDashboardPage
from marketcore.presentation.ui_labels import display_label

API_URL = "http://127.0.0.1:8095/api/kg/v1/edge-pipeline"
SUMMARY_URL = "http://127.0.0.1:8095/api/kg/v1/edge-pipeline/summary"


def _json(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=5) as r:
        return json.loads(r.read().decode("utf-8"))


def _e(v: object) -> str:
    return html.escape("" if v is None else str(v))


def _l(key: str, fallback: str) -> str:
    return display_label(f"edge_pipeline_v2.{key}", fallback)


class EdgePipelineV2Page(BaseDashboardPage):
    page_key = "edge_pipeline_v2"
    route = "/edge-pipeline-v2"
    title = display_label(route, "Этапы V2")
    subtitle = display_label(
        "edge_pipeline_v2.subtitle",
        "Единый снимок состояния кандидатов через Platform API.",
    )
    icon = "🧭"
    menu_order = 346

    def render_body(self) -> str:
        summary = (_json(SUMMARY_URL).get("data") or {})
        rows = (_json(API_URL).get("data") or [])

        cards = "".join(
            f'<section class="fc-card"><b>{_e(_l(label, fallback))}</b><br>{_e(summary.get(label, 0))}</section>'
            for label, fallback in [
                ("total", "Всего"),
                ("research", "Исследование"),
                ("validation", "Проверка"),
                ("robustness", "Устойчивость"),
                ("oos", "OOS"),
                ("risk", "Риск"),
                ("trading", "Торговля"),
            ]
        )

        body = []
        for i, r in enumerate(rows, 1):
            body.append(f"""
            <tr>
              <td>{i}</td>
              <td>{_e(r.get("display_name"))}<br><small>{_e(r.get("symbol"))}</small></td>
              <td>{_e(r.get("asset_class"))}</td>
              <td>{_e(r.get("timeframe"))}</td>
              <td>{_e(r.get("strategy_family"))}</td>
              <td>{_e(r.get("pipeline_stage"))}</td>
              <td>{_e(r.get("overall_status"))}</td>
              <td>{_e(r.get("ranking_score"))}</td>
              <td>{_e(r.get("research_priority"))}</td>
              <td>{_e(r.get("validation_status"))}</td>
              <td>{_e(r.get("robustness_status"))}</td>
              <td>{_e(r.get("oos_status"))}</td>
              <td>{_e(r.get("backtest_status"))}</td>
              <td>{_e(r.get("paper_status"))}</td>
              <td>{_e(r.get("risk_status"))}</td>
              <td>{_e(r.get("trading_status"))}</td>
            </tr>
            """)

        return f"""
        <section class="fc-card">
          <h1>{_e(self.title)}</h1>
          <p>{_e(self.subtitle)}</p>
          <p>Источник: analytics.edge_pipeline_snapshot_v1 → Platform API.</p>
        </section>

        <section class="fc-grid">{cards}</section>

        <section class="fc-card">
          <h2>{_e(_l("candidates", "Кандидаты"))}</h2>
          <table>
            <thead>
              <tr>
                <th>#</th>
                <th>{_e(_l("instrument", "Инструмент"))}</th>
                <th>{_e(_l("asset", "Актив"))}</th>
                <th>TF</th>
                <th>{_e(_l("strategy", "Стратегия"))}</th>
                <th>{_e(_l("stage", "Этап"))}</th>
                <th>{_e(_l("status", "Статус"))}</th>
                <th>Score</th>
                <th>{_e(_l("priority", "Приоритет"))}</th>
                <th>{_e(_l("validation", "Проверка"))}</th>
                <th>{_e(_l("robustness", "Устойчивость"))}</th>
                <th>OOS</th>
                <th>{_e(_l("backtest", "Бэктест"))}</th>
                <th>Paper</th>
                <th>{_e(_l("risk", "Риск"))}</th>
                <th>{_e(_l("trading", "Торговля"))}</th>
              </tr>
            </thead>
            <tbody>{''.join(body)}</tbody>
          </table>
        </section>
        """
