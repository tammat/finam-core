from marketcore_os.services.runtime import RuntimeCenterService
from marketcore_os.widgets.base import badge, row, tr


def render_runtime_center_workspace(lang: str) -> str:
    vm = RuntimeCenterService().get_workspace_model()

    return f"""
<div data-workspace="runtime-center">

<section class="mc-card mc-card-wide mc-next">
<h2>{tr(lang, "Центр Runtime", "Runtime Center")}</h2>
{row(tr(lang, "Статус Runtime", "Runtime Status"), badge(vm.runtime_status, "off" if vm.runtime_status == "OFF" else "info"))}
{row(tr(lang, "Источник", "Source"), vm.data_source)}
</section>

<div class="mc-workspace-grid">

<section class="mc-card">
<h3>{tr(lang, "Исполнение", "Execution")}</h3>
{row("Paper", badge(vm.paper_status, "info"))}
{row("Production", badge(vm.production_status, "off" if vm.production_status == "OFF" else "info"))}
{row(tr(lang, "Риск", "Risk"), badge(vm.risk_status, "ok"))}
</section>

<section class="mc-card">
<h3>{tr(lang, "Активность", "Activity")}</h3>
{row(tr(lang, "Активные инструменты", "Active Symbols"), str(vm.active_symbols))}
{row(tr(lang, "Активные Edge", "Active Edges"), str(vm.active_edges))}
{row(tr(lang, "Открытые позиции", "Open Positions"), str(vm.active_positions))}
</section>

<section class="mc-card">
<h3>{tr(lang, "Сегодня", "Today")}</h3>
{row(tr(lang, "Сигналы", "Signals"), str(vm.signals_today))}
{row(tr(lang, "Сделки", "Trades"), str(vm.trades_today))}
{row("PnL", f"{vm.pnl_today:,.2f}")}
</section>

<section class="mc-card">
<h3>{tr(lang, "Следующее действие", "Next Action")}</h3>
{row(tr(lang, "Этап", "Stage"), vm.next_action)}
</section>

</div>
</div>
"""
