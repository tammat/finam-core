from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class UiResource:
    resource_key: str
    locale_code: str
    caption: str
    caption_short: str
    caption_mobile: str
    tooltip: str
    icon: str
    resource_group: str


ALLOWED_PREFIXES: tuple[str, ...] = (
    "navigation.",
    "page.",
    "button.",
    "table.",
    "column.",
    "dashboard.",
    "strategy.",
    "status.",
    "tooltip.",
    "dialog.",
    "message.",
    "error.",
    "system.",
    "market.",
    "research.",
    "risk.",
    "portfolio.",
    "runtime.",
)


UI_RESOURCES: tuple[UiResource, ...] = (
    UiResource("page.max_edge.title", "ru", "Лучший Edge", "Лучший Edge", "Лучший Edge", "Лучший торговый кандидат", "🎯", "page"),
    UiResource("page.shadow.title", "ru", "Shadow-наблюдение", "Shadow", "Shadow", "Наблюдение кандидатов без исполнения", "👁️", "page"),
    UiResource("page.shadow.daily.title", "ru", "Ежедневная аналитика", "День", "День", "Дневная аналитика shadow-наблюдений", "📊", "page"),

    UiResource("column.symbol", "ru", "Инструмент", "Инструмент", "Инструмент", "Торговый инструмент", "", "column"),
    UiResource("column.strategy", "ru", "Стратегия", "Стратегия", "Стратегия", "Торговая стратегия", "", "column"),
    UiResource("column.score", "ru", "Оценка", "Оценка", "Оценка", "Итоговая оценка", "", "column"),
    UiResource("column.status", "ru", "Статус", "Статус", "Статус", "Статус записи", "", "column"),

    UiResource("status.pass", "ru", "Пройдено", "OK", "OK", "Проверка пройдена", "", "status"),
    UiResource("status.review", "ru", "Требует проверки", "Проверка", "Проверка", "Требуется дополнительная проверка", "", "status"),
    UiResource("status.done", "ru", "Завершено", "Завершено", "Завершено", "Этап завершен", "", "status"),
    UiResource("status.waiting", "ru", "Ожидает", "Ожидает", "Ожидает", "Ожидает обработки", "", "status"),
    UiResource("status.active", "ru", "Активно", "Активно", "Активно", "Активное состояние", "", "status"),
    UiResource("status.disabled", "ru", "Отключено", "Отключено", "Отключено", "Отключенное состояние", "", "status"),

    UiResource("button.refresh", "ru", "Обновить", "Обновить", "Обновить", "Обновить данные", "🔄", "button"),
    UiResource("button.open", "ru", "Открыть", "Открыть", "Открыть", "Открыть страницу", "↗", "button"),
    UiResource("button.back", "ru", "Назад", "Назад", "Назад", "Вернуться назад", "←", "button"),
    UiResource("button.home", "ru", "Главная", "Главная", "Главная", "Перейти на главную", "🏠", "button"),
)
