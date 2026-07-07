from __future__ import annotations

import subprocess

from marketcore.presentation.components import render_data_table, render_kpi_card, render_section
from marketcore.presentation.page import Page


class RuntimeViewPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/runtime-view",
            title="Runtime View",
            icon="🟢",
            menu_order=50,
        )

    def render(self) -> str:
        status = subprocess.run(
            ["systemctl", "is-active", "finam-paper-pipeline.service"],
            check=False,
            capture_output=True,
            text=True,
        ).stdout.strip() or "unknown"

        journal = subprocess.run(
            [
                "journalctl",
                "-u",
                "finam-paper-pipeline.service",
                "--since",
                "30 minutes ago",
                "--no-pager",
                "-n",
                "30",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        rows = [
            {"metric": "paper_pipeline", "value": status},
            {"metric": "journal_window", "value": "30 minutes"},
            {"metric": "execution_enabled", "value": "0"},
            {"metric": "micro_live_allowed", "value": "0"},
        ]

        log_rows = [
            {"line": line[-220:]}
            for line in (journal.stdout or journal.stderr).splitlines()[-30:]
        ]

        kpi = "".join([
            render_kpi_card("Paper pipeline", status, "systemd"),
            render_kpi_card("Execution", "0", "disabled"),
            render_kpi_card("Micro Live", "0", "disabled"),
            render_kpi_card("Logs", len(log_rows), "last 30 lines"),
        ])

        return (
            render_section("Runtime", kpi)
            + render_section("Состояние", render_data_table(["metric", "value"], rows))
            + render_section("Журнал", render_data_table(["line"], log_rows))
        )
