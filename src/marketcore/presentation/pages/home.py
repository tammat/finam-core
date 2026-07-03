from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context


def _link(title: str, href: str, note: str) -> str:
    return f"""
    <a class="link-card" href="{escape(href)}">
      <strong>{escape(title)}</strong>
      <span>{escape(note)}</span>
    </a>
    """


def _metric(title: str, value: str, note: str = "") -> str:
    return f"""
    <section class="card">
        <h2>{escape(title)}</h2>
        <p style="font-size:28px;font-weight:700;margin:8px 0;">{escape(value)}</p>
        <p>{escape(note)}</p>
    </section>
    """


class HomePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/",
            title="MarketCore OS",
            icon="⌂",
            menu_order=10,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        phase = ctx.api_get("/api/kg/v1/phase-ii-paper-edge-discovery-summary")
        daily = ctx.api_get("/api/kg/v1/paper-sample-operations-daily-summary")
        ui_health = ctx.api_get("/api/kg/v1/marketcore-ui-systemd-health")

        phase_data = phase.get("data") or {}
        daily_data = daily.get("data") or {}
        ui_data = ui_health.get("data") or {}

        phase_status = str(phase_data.get("phase_result_status", "UNKNOWN"))
        operational_status = str(phase_data.get("operational_status", "UNKNOWN"))
        daily_status = str(daily_data.get("daily_status", "UNKNOWN"))
        ui_status = str(ui_data.get("overall_status", "UNKNOWN"))

        candidates = ctx.formatter.number(phase_data.get("candidates_total"), 0)
        sample_ready = ctx.formatter.number(phase_data.get("sample_ready"), 0)
        micro_live_allowed = str(phase_data.get("micro_live_allowed", False))

        return f"""
        <section class="card">
            <h2>Рабочий стол MarketCore</h2>
            <p>Единая точка входа: поиск преимущества, накопление выборки, торговый контур, риски, настройки и системное здоровье.</p>
            <p>UI работает через MarketCore UI Shell на 8080. Прямого SQL из страниц нет.</p>
        </section>

        <div style="display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;">
            {_metric("Phase II", phase_status, operational_status)}
            {_metric("Daily Status", daily_status, "Дневная сводка операций")}
            {_metric("UI/Systemd", ui_status, "8080 / 8095")}
            {_metric("Micro Live", micro_live_allowed, "Должно быть False")}
        </div>

        <section class="card">
            <h2>Сводка Paper Edge Discovery</h2>
            <table>
                <thead>
                    <tr><th>Показатель</th><th>Значение</th></tr>
                </thead>
                <tbody>
                    <tr><td>Кандидатов</td><td>{escape(candidates)}</td></tr>
                    <tr><td>Готовы по выборке</td><td>{escape(sample_ready)}</td></tr>
                    <tr><td>Операционный статус</td><td>{escape(operational_status)}</td></tr>
                    <tr><td>Micro Live разрешён</td><td>{escape(micro_live_allowed)}</td></tr>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>Основные разделы</h2>
            <div class="link-grid">
                {_link("Поиск преимущества", "/paper-edge-discovery", "Кандидаты, объяснения, очередь проверки")}
                {_link("Итоги Phase II", "/phase-ii-paper-edge-discovery-summary", "Финальная сводка фазы")}
                {_link("Дневная сводка операций", "/paper-runtime-sample-collection-daily-summary", "Что делать сегодня")}
                {_link("Операции накопления выборки", "/paper-runtime-sample-collection-operations", "Кандидаты ближе всего к повторной проверке")}
                {_link("Накопление выборки", "/paper-sample-accumulation-monitor", "Сколько сделок есть и сколько нужно")}
                {_link("Здоровье операций", "/paper-sample-operations-timer-health", "Timer/service и свежесть данных")}
                {_link("Граф знаний", "/knowledge-graph", "Knowledge Graph, статистика, валидация")}
                {_link("Риски", "/risk", "Risk control и будущие risk gates")}
                {_link("Настройки", "/settings", "Локаль, валюта, таймзона, тема")}
                {_link("Здоровье UI/Systemd", "/marketcore-ui-systemd-health", "KG API 8095 и UI 8080")}
            </div>
        </section>

        <section class="card">
            <h2>Next Action</h2>
            <p>MARKETCORE_UI_8080_HOME_SUMMARY_LINKS_V1</p>
        </section>
        """
