from __future__ import annotations

from marketcore_os.widgets.base import badge, row, tr
from marketcore_os.services.research import ResearchService


def render_edge_workspace(lang: str) -> str:

    vm = ResearchService().get_widget_model()

    return f"""
<div data-workspace="edge">

<section class="mc-card mc-card-wide mc-next">

<h2>{tr(lang,"Edge Center","Edge Center")}</h2>

{row(tr(lang,"Статус","Status"), badge("READY","info"))}

{row(tr(lang,"Источник","Source"), vm.data_source)}

</section>

<div class="mc-workspace-grid" style="margin-top:14px;">

<section class="mc-card">

<h3>Discovery</h3>

{row("Research Candidates", str(vm.research_candidates))}

</section>

<section class="mc-card">

<h3>Forensic</h3>

{row("TOP3", str(vm.paper_ready))}

</section>

<section class="mc-card">

<h3>Robustness</h3>

{row("Pipeline", badge(vm.pipeline_status,"ok"))}

</section>

<section class="mc-card">

<h3>Out Of Sample</h3>

{row("OOS PASS", str(vm.oos_pass))}

</section>

<section class="mc-card">

<h3>Shadow</h3>

{row("Status", badge("READY","info"))}

</section>

<section class="mc-card">

<h3>Paper</h3>

{row("Paper Ready", str(vm.paper_ready))}

</section>

<section class="mc-card mc-card-wide">

<h3>Production</h3>

{row("Runtime", badge("OFF","off"))}

</section>

</div>

</div>
"""
