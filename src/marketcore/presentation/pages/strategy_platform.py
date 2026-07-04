from __future__ import annotations

from html import escape
import json

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


def _bool_label(value: object) -> str:
    return display_label("common.yes" if bool(value) else "common.no")


class StrategyPlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/strategy-platform",
            title=display_label("/strategy-platform"),
            icon="Ψ",
            menu_order=37,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/strategy-platform/summary").get("data") or {}
        registry = ctx.api_get("/api/kg/v1/strategy-platform/registry").get("data") or []
        configs = ctx.api_get("/api/kg/v1/strategy-platform/configuration").get("data") or []
        deps = ctx.api_get("/api/kg/v1/strategy-platform/dependencies").get("data") or []
        signals = ctx.api_get("/api/kg/v1/strategy-platform/signals").get("data") or []

        registry_rows = ""
        for r in registry:
            registry_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_name"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("category"))}</td>
                <td>{_e(_dto_label(r.get("status")))}</td>
                <td>{_e(_bool_label(r.get("enabled")))}</td>
                <td>{_e(_bool_label(r.get("paper_enabled")))}</td>
                <td>{_e(_bool_label(r.get("risk_enabled")))}</td>
                <td>{_e(_bool_label(r.get("live_enabled")))}</td>
                <td>{_e(r.get("priority"))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_json = r.get("config_json") or {}
            config_text = json.dumps(config_json, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("config_version"))}</td>
                <td>{_e(_dto_label(r.get("active_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        dep_rows = ""
        for r in deps:
            dep_rows += f"""
            <tr>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("strategy_version"))}</td>
                <td>{_e(r.get("feature_name"))}</td>
                <td>{_e(_bool_label(r.get("required")))}</td>
                <td>{_e(ctx.formatter.number(r.get("weight"), 4))}</td>
            </tr>
            """

        signal_rows = ""
        for r in signals[:100]:
            signal_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("signal_ts"))}</td>
                <td>{_e(_dto_label(r.get("signal_direction")))}</td>
                <td>{_e(_dto_label(r.get("signal_status")))}</td>
                <td>{_e(ctx.formatter.number(r.get("signal_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("confidence"), 4))}</td>
                <td>{_e(_bool_label(r.get("execution_allowed")))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("strategy.platform.title"))}</h2>
            <p>{_e(_label("strategy.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("strategy.platform.strategies_total"))}</h3><p>{_e(summary.get("strategies_total"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.strategies_enabled"))}</h3><p>{_e(summary.get("strategies_enabled"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.active_configs"))}</h3><p>{_e(summary.get("active_configs"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.signals_total"))}</h3><p>{_e(summary.get("signals_total"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.execution_allowed"))}</h3><p>{_e(summary.get("execution_allowed"))}</p></div>
            <div class="card"><h3>{_e(_label("strategy.platform.health"))}</h3><p>{_e(_dto_label(summary.get("health")))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.registry"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.name"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.category"))}</th>
                        <th>{_e(_label("strategy.platform.status"))}</th>
                        <th>{_e(_label("strategy.platform.active"))}</th>
                        <th>{_e(_label("strategy.platform.paper"))}</th>
                        <th>{_e(_label("strategy.platform.risk"))}</th>
                        <th>{_e(_label("strategy.platform.live"))}</th>
                        <th>{_e(_label("strategy.platform.priority"))}</th>
                    </tr>
                </thead>
                <tbody>{registry_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.config_version"))}</th>
                        <th>{_e(_label("strategy.platform.active"))}</th>
                        <th>{_e(_label("strategy.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.dependencies"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.version"))}</th>
                        <th>{_e(_label("strategy.platform.feature"))}</th>
                        <th>{_e(_label("strategy.platform.required"))}</th>
                        <th>{_e(_label("strategy.platform.weight"))}</th>
                    </tr>
                </thead>
                <tbody>{dep_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("strategy.platform.signals"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("strategy.platform.instrument"))}</th>
                        <th>{_e(_label("strategy.platform.timeframe"))}</th>
                        <th>{_e(_label("strategy.platform.family"))}</th>
                        <th>{_e(_label("strategy.platform.signal_ts"))}</th>
                        <th>{_e(_label("strategy.platform.direction"))}</th>
                        <th>{_e(_label("strategy.platform.status"))}</th>
                        <th>{_e(_label("strategy.platform.score"))}</th>
                        <th>{_e(_label("strategy.platform.confidence"))}</th>
                        <th>{_e(_label("strategy.platform.execution_allowed"))}</th>
                    </tr>
                </thead>
                <tbody>{signal_rows}</tbody>
            </table>
        </section>
        """
