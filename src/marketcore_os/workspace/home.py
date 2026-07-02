from __future__ import annotations

from marketcore_os.widgets.base import badge, row, tr
from marketcore_os.widgets.registry import widgets_for_workspace


def _static_business_cards(lang: str) -> str:
    return f"""
      <section class="mc-card">
        <h3>{tr(lang, "Риск", "Risk")}</h3>
        {row("Runtime", badge("OFF", "off"))}
        {row("Execution", badge("OFF", "off"))}
        {row("Micro Live", badge("OFF", "off"))}
        {row("Daily Risk", "0.0%")}
      </section>
    """


def render_home_workspace(lang: str) -> str:
    widgets = list(widgets_for_workspace("workspace"))

    today = "".join(w.render(lang) for w in widgets if w.widget_id == "W001_TODAY")
    capital = "".join(w.render(lang) for w in widgets if w.widget_id == "W003_CAPITAL")
    profit = "".join(w.render(lang) for w in widgets if w.widget_id == "W004_PROFIT")
    research = "".join(w.render(lang) for w in widgets if w.widget_id == "W005_RESEARCH")
    program = "".join(w.render(lang) for w in widgets if w.widget_id == "W002_PROGRAM")

    return f"""
    <div data-workspace="home">
      {today}

      <div class="mc-workspace-grid" style="margin-top:14px;">
        {capital}
        {profit}
        {research}
        {_static_business_cards(lang)}
        {program}
      </div>
    </div>
    """
