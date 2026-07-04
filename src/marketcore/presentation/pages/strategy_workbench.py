from __future__ import annotations

from html import escape

from marketcore.presentation.page import Page
from marketcore.presentation.presentation_context import build_presentation_context
from marketcore.presentation.ui_labels import display_label


def _e(value: object) -> str:
    return escape("" if value is None else str(value))


def _label(key: str) -> str:
    return display_label(key)


def _signal(value: object) -> str:
    return display_label(f"signal.{value}")


class StrategyWorkbenchPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-workbench",
            title=display_label("/strategy-workbench"),
            icon="⌁",
            menu_order=36,
        )

    def render(self) -> str:
        ctx = build_presentation_context()
        payload = ctx.api_get("/api/kg/v1/strategy-workbench").get("data") or {}

        summary = payload.get("summary") or {}
        rows = payload.get("rows") or []

        body = ""
        for r in rows[:100]:
            body += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("bar_ts"))}</td>
                <td>{_e(_signal(r.get("signal_direction")))}</td>
                <td>{_e(_label('strategy.workbench.' + str(r.get("reason", "")).lower())) if False else _e(r.get("reason"))}</td>
                <td>{_e(ctx.formatter.number(r.get("signal_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("confidence"), 4))}</td>
                <td>{_e(", ".join(r.get("passed_filters") or []))}</td>
                <td>{_e(", ".join(r.get("failed_filters") or []))}</td>
                <td>{_e(ctx.formatter.number(r.get("execution_time_ms"), 3))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.workbench.title"))}</h2>
            <p>{_e(_label("strategy.workbench.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.workbench.features_checked"))}</h3><p>{_e(summary.get("features_checked"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.workbench.signals_found"))}</h3><p>{_e(summary.get("signals_found"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.workbench.strategy"))}</h3><p>{_e(summary.get("strategy_family"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.workbench.rows"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.workbench.instrument"))}</th>
                        <th>{_e(_label("strategy.workbench.timeframe"))}</th>
                        <th>{_e(_label("strategy.workbench.bar"))}</th>
                        <th>{_e(_label("strategy.workbench.signal"))}</th>
                        <th>{_e(_label("strategy.workbench.reason"))}</th>
                        <th>{_e(_label("strategy.workbench.score"))}</th>
                        <th>{_e(_label("strategy.workbench.confidence"))}</th>
                        <th>{_e(_label("strategy.workbench.passed"))}</th>
                        <th>{_e(_label("strategy.workbench.failed"))}</th>
                        <th>{_e(_label("strategy.workbench.execution_time"))}</th>
                    </tr>
                </thead>
                <tbody>{body}</tbody>
            </table>
        </section>
        """
