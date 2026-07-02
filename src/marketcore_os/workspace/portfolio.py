from marketcore_os.services.portfolio import PortfolioService
from marketcore_os.widgets.base import row,badge,tr

def render_portfolio_workspace(lang:str):

    vm=PortfolioService().get_workspace_model()

    return f"""
<div data-workspace="portfolio">

<section class="mc-card mc-card-wide mc-next">

<h2>{tr(lang,"Портфель","Portfolio Workspace")}</h2>

{row(tr(lang,"Статус","Status"),badge(vm.portfolio_status,"info"))}

{row(tr(lang,"Источник","Source"),vm.data_source)}

</section>

<div class="mc-workspace-grid">

<section class="mc-card">

<h3>Capital</h3>

{row("Planned",f"{vm.planned_capital:,.2f}")}
{row("Working",f"{vm.working_capital:,.2f}")}
{row("Available",f"{vm.available_capital:,.2f}")}
{row("PnL",f"{vm.today_pnl:,.2f}")}

</section>

<section class="mc-card">

<h3>Positions</h3>

{row("Open",str(vm.open_positions))}
{row("Paper",str(vm.paper_positions))}
{row("Production",str(vm.production_positions))}
{row("Exposure",f"{vm.exposure_pct:.2f}%")}

</section>

<section class="mc-card mc-card-wide">

<h3>Next Action</h3>

{row("Stage",vm.next_action)}

</section>

</div>

</div>
"""
