from __future__ import annotations

from html import escape

from marketcore_os.layouts.base import tr


def badge(text: str, kind: str = "ok") -> str:
    css = {
        "ok": "mc-ok",
        "info": "mc-info",
        "off": "mc-off",
    }.get(kind, "mc-off")
    return f'<span class="mc-badge {css}">{escape(text)}</span>'


def row(label: str, value: str) -> str:
    return (
        '<div class="mc-row">'
        f'<span class="mc-label">{escape(label)}</span>'
        f'<span class="mc-value">{value}</span>'
        '</div>'
    )


def render_home_workspace(lang: str) -> str:
    return f"""
    <section class="mc-card mc-card-wide mc-next">
      <h2>{escape(tr(lang, "Сегодня", "Today"))}</h2>
      {row(tr(lang, "Следующее действие", "Next Action"), "TOP3_PAPER_RUNTIME_EXECUTION_V1")}
      {row(tr(lang, "Статус", "Status"), badge("READY"))}
    </section>

    <div class="mc-workspace-grid" style="margin-top:14px;">
      <section class="mc-card">
        <h3>{escape(tr(lang, "Капитал", "Capital"))}</h3>
        {row(tr(lang, "Плановый капитал", "Planned capital"), "500 000 ₽")}
        {row(tr(lang, "Работает", "Working"), "0%")}
        {row(tr(lang, "Свободно", "Available"), "100%")}
        {row(tr(lang, "Сегодня", "Today"), "+0.00%")}
      </section>

      <section class="mc-card">
        <h3>{escape(tr(lang, "Двигатель прибыли", "Profit Engine"))}</h3>
        {row("Production", "0")}
        {row("Paper", "3")}
        {row("Shadow", "0")}
        {row("Research Candidate", "54")}
      </section>

      <section class="mc-card">
        <h3>{escape(tr(lang, "Исследования", "Research"))}</h3>
        {row("Pipeline", badge("COMPLETE"))}
        {row("TOP3 Validation", badge("COMPLETE"))}
        {row("Edge Factory", badge("READY", "info"))}
      </section>

      <section class="mc-card">
        <h3>{escape(tr(lang, "Риск", "Risk"))}</h3>
        {row("Runtime", badge("OFF", "off"))}
        {row("Execution", badge("OFF", "off"))}
        {row("Micro Live", badge("OFF", "off"))}
        {row("Daily Risk", "0.0%")}
      </section>

      <section class="mc-card mc-card-wide">
        <h3>{escape(tr(lang, "Статус программы", "Program Status"))}</h3>
        {row("Q3 2026", badge("ACTIVE", "info"))}
        {row("Platform", badge("COMPLETE"))}
        {row("Research", badge("COMPLETE"))}
        {row("TOP3", badge("COMPLETE"))}
        {row("Paper", badge("READY", "info"))}
        {row("MarketCore OS", badge("IN PROGRESS", "info"))}
      </section>
    </div>
    """
