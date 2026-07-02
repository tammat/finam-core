from __future__ import annotations

from marketcore_os.services.research import ResearchService
from marketcore_os.widgets.base import badge, row, tr


def render_research_workspace(lang: str) -> str:
    vm = ResearchService().get_widget_model()

    return f"""
<div data-workspace="research">

<section class="mc-card mc-card-wide mc-next">
<h2>{tr(lang,"Исследования","Исследования")}</h2>

{row(tr(lang,"Статус","Status"), badge("READY","info"))}

{row(tr(lang,"Источник","Source"), vm.data_source)}

</section>

<div class="mc-workspace-grid" style="margin-top:14px;">

<section class="mc-card">

<h3>{tr(lang,"Pipeline","Pipeline")}</h3>

{row("Pipeline", badge(vm.pipeline_status,"ok"))}

{row("TOP3", badge(vm.top3_status,"ok"))}

{row("Edge Factory", badge(vm.edge_factory_status,"info"))}

</section>

<section class="mc-card">

<h3>{tr(lang,"Статистика","Statistics")}</h3>

{row("Research Candidates", str(vm.research_candidates))}
{row("OOS PASS", str(vm.oos_pass))}
{row("Paper Ready", str(vm.paper_ready))}

</section>

<section class="mc-card mc-card-wide">

<h3>{tr(lang,"Следующее действие","Next Action")}</h3>

{row(
tr(lang,"Этап","Stage"),
"GLOBAL_EDGE_FORENSIC_AUDIT_V1"
)}

</section>

</div>

</div>
"""
