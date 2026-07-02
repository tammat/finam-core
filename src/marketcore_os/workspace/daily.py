from marketcore_os.services.daily import DailyCenterService
from marketcore_os.widgets.base import badge, row, tr


def render_daily_center_workspace(lang: str) -> str:
    vm = DailyCenterService().get_workspace_model()

    return f"""
<div data-workspace="daily-center">

<section class="mc-card mc-card-wide mc-next">
<h2>{tr(lang, "Центр дня", "Daily Center")}</h2>
{row(tr(lang, "Статус дня", "Day Status"), badge(vm.day_status, "info"))}
{row(tr(lang, "Источник", "Source"), vm.data_source)}
</section>

<div class="mc-workspace-grid">

<section class="mc-card">
<h3>{tr(lang, "Состояние системы", "System State")}</h3>
{row(tr(lang, "Капитал", "Capital"), badge(vm.capital_status, "info"))}
{row(tr(lang, "Исследования", "Research"), badge(vm.research_status, "info"))}
{row(tr(lang, "Риск", "Risk"), badge(vm.risk_status, "ok"))}
{row("Runtime", badge(vm.runtime_status, "off"))}
</section>

<section class="mc-card">
<h3>{tr(lang, "Что делать сейчас", "What To Do Now")}</h3>
{row(tr(lang, "Следующее действие", "Next Action"), vm.next_action)}
{row(tr(lang, "Подсказка", "Hint"), vm.decision_hint)}
</section>

</div>
</div>
"""
