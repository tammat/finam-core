from marketcore_os.services.capital_manager import CapitalManagerService
from marketcore_os.widgets.base import badge, row, tr


def render_capital_manager_workspace(lang: str) -> str:
    vm = CapitalManagerService().get_workspace_model()

    return f"""
<div data-workspace="capital-manager">

<section class="mc-card mc-card-wide mc-next">
<h2>{tr(lang, "Управление капиталом", "Capital Manager")}</h2>
{row(tr(lang, "Статус", "Status"), badge(vm.manager_status, "info"))}
{row(tr(lang, "Источник", "Source"), vm.data_source)}
</section>

<div class="mc-workspace-grid">

<section class="mc-card">
<h3>Capital</h3>
{row("Planned", f"{vm.planned_capital:,.2f}")}
{row("Working", f"{vm.working_capital:,.2f}")}
{row("Available", f"{vm.available_capital:,.2f}")}
</section>

<section class="mc-card">
<h3>Risk Control</h3>
{row("Exposure", f"{vm.exposure_pct:.2f}%")}
{row("Deployment Limit", f"{vm.deployment_limit_pct:.2f}%")}
{row("Risk Mode", badge(vm.risk_mode, "off"))}
</section>

<section class="mc-card mc-card-wide">
<h3>Next Action</h3>
{row("Stage", vm.next_action)}
</section>

</div>
</div>
"""
