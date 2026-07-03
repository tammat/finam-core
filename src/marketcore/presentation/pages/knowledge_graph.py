from __future__ import annotations

from marketcore.presentation.page import Page


class KnowledgeGraphPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/knowledge-graph",
            title="Граф знаний",
            icon="◎",
            menu_order=30,
        )

    def render(self) -> str:
        return """
        <section class="card">
            <h2>Граф знаний</h2>
            <p>Раздел восстановлен. Ошибка 500 устранена безопасной заглушкой без прямого SQL.</p>
            <p>Следующий этап: подключить реальные метрики Knowledge Graph через KG API.</p>
        </section>

        <section class="card">
            <h2>Связанные разделы</h2>
            <p><a href="/market-universe-ranking">Рейтинг рыночной вселенной</a></p>
            <p><a href="/market-universe-research-queue">Research Queue</a></p>
            <p><a href="/marketcore-ui-route-health-matrix">Матрица маршрутов UI</a></p>
        </section>
        """
