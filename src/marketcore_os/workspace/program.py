from __future__ import annotations

from marketcore_os.services.program import ProgramService
from marketcore_os.widgets.base import badge, row, tr


def render_program_workspace(lang: str) -> str:

    vm = ProgramService().get_widget_model()

    return f"""
<div data-workspace="program">

<section class="mc-card mc-card-wide mc-next">

<h2>{tr(lang,"Программа","Program Workspace")}</h2>

{row(tr(lang,"Статус","Status"), badge("READY","info"))}

{row(tr(lang,"Источник","Source"), vm.data_source)}

</section>

<div class="mc-workspace-grid">

<section class="mc-card">

<h3>Roadmap</h3>

{row("Quarter", vm.quarter)}
{row("Platform", badge(vm.platform_status,"ok"))}
{row("Research", badge(vm.research_status,"ok"))}

</section>

<section class="mc-card">

<h3>Validation</h3>

{row("TOP3", badge(vm.top3_status,"ok"))}
{row("Paper", badge(vm.paper_status,"info"))}

</section>

<section class="mc-card">

<h3>MarketCore OS</h3>

{row("Status", badge(vm.marketcore_status,"info"))}

</section>

<section class="mc-card">

<h3>Next Stage</h3>

{row("Next","MARKETCORE_PORTFOLIO_WORKSPACE_V1")}

</section>

</div>

</div>
"""
