from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context
from marketcore.presentation.ui_labels import display_label


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _label(key: str) -> str:
    return display_label(key)


def _dto_label(dto: object) -> str:
    if isinstance(dto, dict):
        return display_label(str(dto.get("display_key") or "status.UNKNOWN"))
    return display_label(f"status.{dto or 'UNKNOWN'}")


class StrategyGovernancePage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-governance",
            title=display_label("/strategy-governance"),
            icon="◇",
            menu_order=38,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        data = ctx.api_get("/api/kg/v1/strategy-platform/governance").get("data") or {}

        checks = [
            ("strategy.governance.registry", "registry_status"),
            ("strategy.governance.configuration", "configuration_status"),
            ("strategy.governance.dependency", "dependency_status"),
            ("strategy.governance.builder", "builder_status"),
            ("strategy.governance.signal_store", "signal_store_status"),
            ("strategy.governance.api", "api_status"),
            ("strategy.governance.ui", "ui_status"),
        ]

        rows = ""
        for label_key, field in checks:
            rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(data.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.governance.title"))}</h2>
            <p>{_e(_label("strategy.governance.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.governance.overall"))}</h3><p>{_e(_dto_label(data.get("overall_status")))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.governance.readiness"))}</h3><p>{_e(_dto_label(data.get("readiness_status")))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.governance.score"))}</h3><p>{_e(ctx.formatter.number(data.get("governance_score"), 2))}</p></div>
            <div class="card"><h3>Signals</h3><p>{_e(data.get("signal_rows"))}</p></div>
            <div class="card"><h3>Unsafe</h3><p>{_e(data.get("unsafe_execution_rows"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.governance.integrity"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>Block</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody>{rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.governance.recommendation"))}</h2>
            <p>{_e(data.get("recommendation"))}</p>
        </section>
        """
