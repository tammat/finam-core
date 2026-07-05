from __future__ import annotations

import json
from html import escape
from pathlib import Path

from marketcore.presentation.page import Page


AUDIT_JSON = Path("reports/edge_pipeline_audit_latest.json")
AUDIT_TXT = Path("reports/edge_pipeline_audit_latest.txt")


def _load_audit() -> dict:
    if AUDIT_JSON.exists():
        return json.loads(AUDIT_JSON.read_text(encoding="utf-8"))
    return {"summary": {}, "funnel": [], "bottleneck": ["NO_REPORT", 0, 0, 0]}


def _read_report() -> str:
    if AUDIT_TXT.exists():
        return AUDIT_TXT.read_text(encoding="utf-8")
    return "EDGE_PIPELINE_AUDIT_REPORT_NOT_FOUND"


def _kpi(title: str, value: object) -> str:
    return f'<div class="kpi"><div class="kpi-label">{escape(title)}</div><div class="kpi-value">{escape(str(value))}</div></div>'


class EdgeFactoryPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-factory",
            title="Edge Factory",
            icon="🏭",
            menu_order=45,
        )

    def render(self) -> str:
        audit = _load_audit()
        summary = audit.get("summary", {})
        funnel = audit.get("funnel", [])
        bottleneck = audit.get("bottleneck", ["NONE", 0, 0, 0])
        report = escape(_read_report())

        kpis = "".join([
            _kpi("Strategies", summary.get("strategies", 0)),
            _kpi("Research Queue", summary.get("research_queue", 0)),
            _kpi("Observations", summary.get("observations", 0)),
            _kpi("With Trades", summary.get("observations_with_trades", 0)),
            _kpi("Candidates", summary.get("candidates", 0)),
            _kpi("Validated", summary.get("validated", 0)),
            _kpi("Paper", summary.get("paper", 0)),
            _kpi("Research Trades", summary.get("research_trades", 0)),
        ])

        funnel_rows = "".join(
            f"<tr><td>{escape(str(x[0]))}</td><td>{x[1]}</td><td>{x[2]}</td><td>{x[3]}%</td></tr>"
            for x in funnel
        )

        return f"""
        <div class="card">
            <h2>Edge Factory</h2>
            <p>Главный экран исследовательской фабрики: Sprint, Audit, KPI, Bottleneck.</p>
        </div>

        <div class="kpi-grid">{kpis}</div>

        <div class="card">
            <h3>Current Bottleneck</h3>
            <p><b>{escape(str(bottleneck[0]))}</b>: {escape(str(bottleneck[3]))}%</p>
        </div>

        <div class="card">
            <h3>Pipeline Funnel</h3>
            <table>
                <thead>
                    <tr><th>Stage</th><th>Value</th><th>Base</th><th>Conversion</th></tr>
                </thead>
                <tbody>{funnel_rows}</tbody>
            </table>
        </div>

        <div class="card">
            <h3>Latest Audit Report</h3>
            <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{report}</pre>
        </div>
        """
