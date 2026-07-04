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


class EdgePlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/edge-platform",
            title=display_label("/edge-platform"),
            icon="◇",
            menu_order=39,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/edge-platform/summary").get("data") or {}
        decisions = ctx.api_get("/api/kg/v1/edge-platform/decisions").get("data") or []
        configs = ctx.api_get("/api/kg/v1/edge-platform/configuration").get("data") or []
        governance = ctx.api_get("/api/kg/v1/edge-platform/governance").get("data") or {}

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
                <td>{_e(_dto_label(r.get("decision")))}</td>
                <td>{_e(_dto_label(r.get("recommendation")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_replay")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_paper")))}</td>
                <td>{_e(_bool_label(r.get("ready_for_live")))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_text = json.dumps(r.get("config_json") or {}, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("edge_name"))}</td>
                <td>{_e(_dto_label(r.get("enabled_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        governance_rows = ""
        for label_key, field in [
            ("edge.platform.score_engine", "score_engine_status"),
            ("edge.platform.validation", "validation_status"),
            ("edge.platform.decision_engine", "decision_status"),
            ("edge.platform.api", "api_status"),
            ("edge.platform.ui", "ui_status"),
        ]:
            governance_rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(governance.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("edge.platform.title"))}</h2>
            <p>{_e(_label("edge.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("edge.platform.edge_rows"))}</h3><p>{_e(summary.get("edge_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.allow_rows"))}</h3><p>{_e(summary.get("allow_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.observe_rows"))}</h3><p>{_e(summary.get("observe_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.block_rows"))}</h3><p>{_e(summary.get("block_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.ready_for_paper"))}</h3><p>{_e(summary.get("ready_for_paper_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.unsafe_live"))}</h3><p>{_e(summary.get("unsafe_live_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.avg_edge_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_edge_score"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("edge.platform.avg_validation_score"))}</h3><p>{_e(ctx.formatter.number(summary.get("avg_validation_score"), 4))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.decisions"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.instrument"))}</th>
                        <th>{_e(_label("edge.platform.strategy"))}</th>
                        <th>{_e(_label("edge.platform.timeframe"))}</th>
                        <th>{_e(_label("edge.platform.signal_ts"))}</th>
                        <th>{_e(_label("edge.platform.edge_score"))}</th>
                        <th>{_e(_label("edge.platform.validation_score"))}</th>
                        <th>{_e(_label("edge.platform.decision"))}</th>
                        <th>{_e(_label("edge.platform.recommendation"))}</th>
                        <th>{_e(_label("edge.platform.replay"))}</th>
                        <th>{_e(_label("edge.platform.paper"))}</th>
                        <th>{_e(_label("edge.platform.live"))}</th>
                    </tr>
                </thead>
                <tbody>{decision_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.edge_name"))}</th>
                        <th>{_e(_label("edge.platform.enabled"))}</th>
                        <th>{_e(_label("edge.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("edge.platform.governance"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("edge.platform.governance"))}</th>
                        <th>{_e(_label("edge.platform.readiness"))}</th>
                    </tr>
                </thead>
                <tbody>{governance_rows}</tbody>
            </table>
        </section>
        """
