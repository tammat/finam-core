from __future__ import annotations

from marketcore_os.services.capital import CapitalService
from marketcore_os.widgets.base import badge, row, tr
from marketcore_os.widgets.capital import money, pct


def render_capital_workspace(lang: str, currency: str = "RUB") -> str:
    vm = CapitalService().get_widget_model(display_currency=currency)

    return f"""
    <div data-workspace="capital">
      <section class="mc-card mc-card-wide mc-next">
        <h2>{tr(lang, "Капитал", "Capital")}</h2>
        {row(tr(lang, "Статус", "Status"), badge("READY", "info"))}
        {row(tr(lang, "Источник", "Source"), vm.data_source)}
      </section>

      <div class="mc-workspace-grid" style="margin-top:14px;">
        <section class="mc-card">
          <h3>{tr(lang, "Сводка капитала", "Capital Summary")}</h3>
          {row(tr(lang, "Плановый капитал", "Planned capital"), money(vm.planned_capital, vm.display_currency))}
          {row(tr(lang, "Работает", "Working"), money(vm.working_capital, vm.display_currency))}
          {row(tr(lang, "Свободно", "Available"), money(vm.available_capital, vm.display_currency))}
          {row(tr(lang, "PnL сегодня", "Today PnL"), money(vm.today_pnl, vm.display_currency))}
        </section>

        <section class="mc-card">
          <h3>{tr(lang, "Распределение", "Allocation")}</h3>
          {row(tr(lang, "Работает", "Working"), pct(vm.working_pct))}
          {row(tr(lang, "Свободно", "Available"), pct(vm.available_pct))}
          {row(tr(lang, "Базовая валюта", "Base currency"), vm.base_currency)}
          {row(tr(lang, "Валюта отображения", "Display currency"), vm.display_currency)}
        </section>

        <section class="mc-card">
          <h3>{tr(lang, "FX", "FX")}</h3>
          {row(tr(lang, "Источник курса", "FX source"), vm.fx_source)}
          {row(tr(lang, "Правило", "Rule"), tr(lang, "Расчёты в RUB", "Calculations in RUB"))}
          {row(tr(lang, "Конвертация", "Conversion"), tr(lang, "Только отображение", "Display only"))}
        </section>

        <section class="mc-card">
          <h3>{tr(lang, "Риск капитала", "Capital Risk")}</h3>
          {row(tr(lang, "Daily Risk", "Daily Risk"), "0.00%")}
          {row(tr(lang, "Runtime", "Runtime"), badge("OFF", "off"))}
          {row(tr(lang, "Execution", "Execution"), badge("OFF", "off"))}
        </section>
      </div>
    </div>
    """
