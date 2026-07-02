from __future__ import annotations

from marketcore_os.widgets.base import SimpleWidget, badge, row, tr


class TodayWidget(SimpleWidget):
    def __init__(self) -> None:
        super().__init__(
            widget_id="W001_TODAY",
            title_ru="Сегодня",
            title_en="Today",
            priority=10,
            refresh_interval_sec=15,
            workspace="workspace",
        )

    def body(self, lang: str) -> str:
        return (
            row(
                tr(lang, "Следующее действие", "Next Action"),
                "TOP3_PAPER_RUNTIME_EXECUTION_V1",
            )
            + row(tr(lang, "Статус", "Status"), badge("READY", "ok"))
            + row(tr(lang, "Система", "System"), badge("ONLINE", "info"))
            + row(tr(lang, "Режим", "Mode"), badge("READ ONLY", "off"))
        )


today_widget = TodayWidget()
