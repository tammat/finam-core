from __future__ import annotations

from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


class ProgramWidget(SimpleWidget):
    def __init__(self) -> None:
        super().__init__(
            widget_id="W002_PROGRAM",
            title_ru="Статус программы",
            title_en="Program Status",
            priority=90,
            refresh_interval_sec=60,
            workspace="workspace",
        )

    def body(self, lang: str) -> str:
        return (
            row("Q3 2026", badge("ACTIVE", "info"))
            + row(tr(lang, "Платформа", "Platform"), badge("COMPLETE", "ok"))
            + row(tr(lang, "Исследования", "Research"), badge("COMPLETE", "ok"))
            + row("TOP3", badge("COMPLETE", "ok"))
            + row("Paper", badge("READY", "info"))
            + row("MarketCore OS", badge("IN PROGRESS", "info"))
        )


program_widget = ProgramWidget()
