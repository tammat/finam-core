from __future__ import annotations

from html import escape
from pathlib import Path

from marketcore.presentation.page import Page


REPORT_TXT = Path("reports/edge_pipeline_audit_latest.txt")
REPORT_HTML = Path("reports/edge_pipeline_audit_latest.html")


def _read_report() -> str:
    if REPORT_TXT.exists():
        return REPORT_TXT.read_text(encoding="utf-8")
    if REPORT_HTML.exists():
        return REPORT_HTML.read_text(encoding="utf-8")
    return "EDGE_PIPELINE_AUDIT_REPORT_NOT_FOUND"


class EdgeAuditPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-audit",
            title="Edge Audit",
            icon="🔎",
            menu_order=46,
        )

    def render(self) -> str:
        report = escape(_read_report())
        return f"""
        <div class="card">
            <h2>Edge Audit</h2>
            <p>Последний отчёт EDGE Pipeline Audit. Обновляется timer'ом каждые 30 минут.</p>
        </div>
        <div class="card">
            <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{report}</pre>
        </div>
        """
