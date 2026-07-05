from __future__ import annotations

from html import escape
from pathlib import Path

from marketcore.presentation.layout import render_layout


REPORT_TXT = Path("reports/edge_pipeline_audit_latest.txt")
REPORT_HTML = Path("reports/edge_pipeline_audit_latest.html")


def render_edge_audit_page() -> str:
    if REPORT_TXT.exists():
        report = REPORT_TXT.read_text(encoding="utf-8")
    elif REPORT_HTML.exists():
        report = REPORT_HTML.read_text(encoding="utf-8")
    else:
        report = "EDGE_PIPELINE_AUDIT_REPORT_NOT_FOUND"

    content = f"""
    <div class="card">
        <h2>Edge Audit</h2>
        <p>Последний отчёт EDGE Pipeline Audit. Обновляется timer'ом каждые 30 минут.</p>
    </div>
    <div class="card">
        <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{escape(report)}</pre>
    </div>
    """
    return render_layout(title="Edge Audit", active_route="/edge-audit", content=content)
