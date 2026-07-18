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
    UiResource("column.priority", "ru", "№", "№", "№", "Приоритет исследования", "", "column"),
    UiResource("column.timeframe", "ru", "ТФ", "ТФ", "ТФ", "Таймфрейм", "", "column"),
    UiResource("column.stage", "ru", "Этап", "Этап", "Этап", "Этап жизненного цикла", "", "column"),
    UiResource("column.future.bars", "ru", "Накоплено", "Накопл.", "Накопл.", "Накоплено будущих баров", "", "column"),
    UiResource("column.required.bars", "ru", "Нужно", "Нужно", "Нужно", "Минимум будущих баров", "", "column"),
    UiResource("column.state", "ru", "Статус", "Статус", "Статус", "Текущее состояние", "", "column"),
    UiResource("column.position", "ru", "Позиция", "Позиция", "Поз.", "Состояние Paper-позиции", "", "column"),
    UiResource("column.paper.pnl", "ru", "Paper PnL", "PnL", "PnL", "Финансовый результат модельных сделок", "", "column"),
    UiResource("column.risk", "ru", "Риск", "Риск", "Риск", "Последнее решение риск-контроля", "", "column"),
    UiResource("research.control.section.swing.lifecycle.title", "ru", "Swing · Paper", "Swing", "Swing", "Автономный путь OOS → Forward → Shadow → Paper; LIVE отключён", "", "research"),
    UiResource("research.control.section.swing_lifecycle.title", "ru", "Swing · Paper", "Swing", "Swing", "Автономный путь OOS → Forward → Shadow → Paper; LIVE отключён", "", "research"),

    UiResource("status.pass", "ru", "Пройдено", "OK", "OK", "Проверка пройдена", "", "status"),
    UiResource("status.review", "ru", "Требует проверки", "Проверка", "Проверка", "Требуется дополнительная проверка", "", "status"),
    UiResource("status.done", "ru", "Завершено", "Завершено", "Завершено", "Этап завершен", "", "status"),
    UiResource("status.completed", "ru", "Завершено", "Завершено", "Завершено", "Этап завершён", "", "status"),
    UiResource("status.waiting", "ru", "Ожидает", "Ожидает", "Ожидает", "Ожидает обработки", "", "status"),
    UiResource("status.active", "ru", "Активно", "Активно", "Активно", "Активное состояние", "", "status"),
    UiResource("status.disabled", "ru", "Отключено", "Отключено", "Отключено", "Отключенное состояние", "", "status"),

    UiResource("button.refresh", "ru", "Обновить", "Обновить", "Обновить", "Обновить данные", "🔄", "button"),
    UiResource("button.open", "ru", "Открыть", "Открыть", "Открыть", "Открыть страницу", "↗", "button"),
    UiResource("button.back", "ru", "Назад", "Назад", "Назад", "Вернуться назад", "←", "button"),
    UiResource("button.home", "ru", "Главная", "Главная", "Главная", "Перейти на главную", "🏠", "button"),
)
