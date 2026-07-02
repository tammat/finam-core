from __future__ import annotations

from marketcore.presentation.page import Page


class OrdersPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/orders",
            title="Orders",
            icon="⇄",
            menu_order=60,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Orders</h2>
            <p>Раздел подключён к MarketCore UI Shell. Функциональное наполнение будет добавлено отдельным этапом.</p>
        </section>
        """
