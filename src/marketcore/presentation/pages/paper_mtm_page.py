from __future__ import annotations

import subprocess
from html import escape

from marketcore.presentation.page import Page


class PaperMtmPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/paper-mtm",
            title="Paper MTM",
            icon="📊",
            menu_order=47,
        )

    def render(self) -> str:
        sql = """
SELECT
  candidate_id,
  strategy_code,
  symbol,
  timeframe,
  trades,
  round(net_pnl,6) AS net_pnl,
  round(max_drawdown,6) AS max_drawdown,
  paper_status,
  mtm_ts
FROM analytics.paper_portfolio_mtm_v1
ORDER BY mtm_ts DESC, net_pnl DESC
LIMIT 50;
"""
        result = subprocess.run(
            ["psql", "-d", "finam_core", "-c", sql],
            check=False,
            capture_output=True,
            text=True,
        )
        body = escape(result.stdout if result.returncode == 0 else result.stderr)

        return f"""
        <div class="card">
            <h2>Paper MTM</h2>
            <p>Mark-to-market по активным paper-кандидатам. Micro Live и Live не включаются.</p>
        </div>
        <div class="card">
            <pre style="white-space:pre-wrap;font-size:12px;line-height:1.35">{body}</pre>
        </div>
        """
