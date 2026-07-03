from __future__ import annotations

from marketcore.presentation.page import Page


class SettingsPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/settings",
            title="Настройки",
            icon="⚙",
            menu_order=120,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Настройки</h2>
            <p>Раздел подключён к MarketCore UI Shell. Здесь будут настройки локали, валюты, таймзоны, темы и API.</p>
        </section>
        """
