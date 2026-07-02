from marketcore_os.services.intraday import IntradayService
from marketcore_os.widgets.base import row,badge,tr

def render_intraday_workspace(lang:str):

    vm=IntradayService().get_workspace_model()

    return f"""
<div data-workspace="intraday">

<section class="mc-card mc-card-wide mc-next">

<h2>{tr(lang,"Интрадей","Интрадей")}</h2>

{row("Runtime",badge(vm.runtime_status,"info"))}

{row("Paper",badge(vm.paper_status,"ok"))}

{row("Production",badge(vm.production_status,"info"))}

{row(tr(lang,"Источник","Source"),vm.data_source)}

</section>

<div class="mc-workspace-grid">

<section class="mc-card">

<h3>{tr(lang,"Активность","Activity")}</h3>

{row("Active Symbols",str(vm.active_symbols))}
{row("Active Edge",str(vm.active_edges))}
{row("Open Positions",str(vm.active_positions))}
{row("Exposure",f"{vm.exposure_pct:.2f}%")}

</section>

<section class="mc-card">

<h3>{tr(lang,"Следующий этап","Next")}</h3>

{row("Stage",vm.next_action)}

</section>

</div>

</div>
"""
