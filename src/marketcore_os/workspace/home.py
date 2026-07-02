from __future__ import annotations

from marketcore_os.widgets.base import badge, row, tr
from marketcore_os.widgets.registry import widgets_for_workspace


def _static_business_cards(lang: str) -> str:
    return f"""
    """


def render_home_workspace(lang: str) -> str:
    widgets = list(widgets_for_workspace("workspace"))

    today = "".join(w.render(lang) for w in widgets if w.widget_id == "W001_TODAY")
    capital = "".join(w.render(lang) for w in widgets if w.widget_id == "W003_CAPITAL")
    profit = "".join(w.render(lang) for w in widgets if w.widget_id == "W004_PROFIT")
    research = "".join(w.render(lang) for w in widgets if w.widget_id == "W005_RESEARCH")
    risk = "".join(w.render(lang) for w in widgets if w.widget_id == "W006_RISK")
    program = "".join(w.render(lang) for w in widgets if w.widget_id == "W002_PROGRAM")

    return f"""
    <div data-workspace="home">
      {today}

      <div class="mc-workspace-grid" style="margin-top:14px;">
        {capital}
        {profit}
        {research}
        {risk}
        {_static_business_cards(lang)}
        {program}
      </div>
    </div>
    """
