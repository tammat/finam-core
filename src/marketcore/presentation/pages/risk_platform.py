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


class RiskPlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/risk-platform",
            title=display_label("/risk-platform"),
            icon="◆",
            menu_order=40,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/risk-platform/summary").get("data") or {}
        decisions = ctx.api_get("/api/kg/v1/risk-platform/decisions").get("data") or []
        configs = ctx.api_get("/api/kg/v1/risk-platform/configuration").get("data") or []
        governance = ctx.api_get("/api/kg/v1/risk-platform/governance").get("data") or {}

        decision_rows = ""
        for r in decisions[:100]:
            decision_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("strategy_family"))}</td>
                <td>{_e(r.get("timeframe"))}</td>
                <td>{_e(r.get("signal_ts"))}</td>
                <td>{_e(ctx.formatter.number(r.get("edge_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("validation_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("risk_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("position_risk_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("exposure_risk_score"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("kill_switch_score"), 4))}</td>
                <td>{_e(_dto_label(r.get("risk_decision")))}</td>
                <td>{_e(_dto_label(r.get("recommendation")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_paper")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_live")))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_text = json.dumps(r.get("config_json") or {}, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("risk_name"))}</td>
                <td>{_e(_dto_label(r.get("enabled_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        governance_rows = ""
        for label_key, field in [
            ("risk.platform.rule_engine", "rule_engine_status"),
            ("risk.platform.builder", "builder_status"),
            ("risk.platform.decision_engine", "decision_status"),
            ("risk.platform.api", "api_status"),
            ("risk.platform.ui", "ui_status"),
        ]:
            governance_rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(governance.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("risk.platform.title"))}</h2>
            <p>{_e(_label("risk.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("risk.platform.risk_rows"))}</h3><p>{_e(summary.get("risk_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.allow_rows"))}</h3><p>{_e(summary.get("allow_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.observe_rows"))}</h3><p>{_e(summary.get("observe_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.block_rows"))}</h3><p>{_e(summary.get("block_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.ready_for_paper"))}</h3><p>{_e(summary.get("ready_for_paper_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.unsafe_live"))}</h3><p>{_e(summary.get("unsafe_live_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.avg_risk_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_risk_score"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.avg_position_risk_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_position_risk_score"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("risk.platform.avg_exposure_risk_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_exposure_risk_score"), 4))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("risk.platform.decisions"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("risk.platform.instrument"))}</th>
                        <th>{_e(_label("risk.platform.strategy"))}</th>
                        <th>{_e(_label("risk.platform.timeframe"))}</th>
                        <th>{_e(_label("risk.platform.signal_ts"))}</th>
                        <th>{_e(_label("risk.platform.edge_score"))}</th>
                        <th>{_e(_label("risk.platform.validation_score"))}</th>
                        <th>{_e(_label("risk.platform.risk_score"))}</th>
                        <th>{_e(_label("risk.platform.position_risk"))}</th>
                        <th>{_e(_label("risk.platform.exposure_risk"))}</th>
                        <th>{_e(_label("risk.platform.kill_switch"))}</th>
                        <th>{_e(_label("risk.platform.decision"))}</th>
                        <th>{_e(_label("risk.platform.recommendation"))}</th>
                        <th>{_e(_label("risk.platform.paper"))}</th>
                        <th>{_e(_label("risk.platform.live"))}</th>
                    </tr>
                </thead>
                <tbody>{decision_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("risk.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("risk.platform.risk_name"))}</th>
                        <th>{_e(_label("risk.platform.enabled"))}</th>
                        <th>{_e(_label("risk.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("risk.platform.governance"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("risk.platform.governance"))}</th>
                        <th>{_e(_label("risk.platform.readiness"))}</th>
                    </tr>
                </thead>
                <tbody>{governance_rows}</tbody>
            </table>
        </section>
        """
