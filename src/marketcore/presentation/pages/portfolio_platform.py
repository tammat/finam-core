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


class PortfolioPlatformPage(Page):
    def __init__(self) -> None:
        super().__init__(
            route="/portfolio-platform",
            title=display_label("/portfolio-platform"),
            icon="◉",
            menu_order=42,
        )

    def render(self) -> str:
        ctx = build_presentation_context()

        summary = ctx.api_get("/api/kg/v1/portfolio-platform/summary").get("data") or {}
        positions = ctx.api_get("/api/kg/v1/portfolio-platform/positions").get("data") or []
        equity = ctx.api_get("/api/kg/v1/portfolio-platform/equity").get("data") or {}
        configs = ctx.api_get("/api/kg/v1/portfolio-platform/configuration").get("data") or []
        governance = ctx.api_get("/api/kg/v1/portfolio-platform/governance").get("data") or {}

        position_rows = ""
        for r in positions[:100]:
            position_rows += f"""
            <tr>
                <td>{_e(r.get("symbol"))}</td>
                <td>{_e(r.get("asset_class"))}</td>
                <td>{_e(ctx.formatter.number(r.get("quantity"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("avg_price"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("last_price"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("market_value"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("unrealized_pnl"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("realized_pnl"), 4))}</td>
                <td>{_e(ctx.formatter.number(r.get("exposure"), 4))}</td>
                <td>{_e(_dto_label(r.get("position_status")))}</td>
            </tr>
            """

        config_rows = ""
        for r in configs:
            config_text = json.dumps(r.get("config_json") or {}, ensure_ascii=False, sort_keys=True)
            config_rows += f"""
            <tr>
                <td>{_e(r.get("portfolio_name"))}</td>
                <td>{_e(_dto_label(r.get("enabled_status")))}</td>
                <td><code>{_e(config_text)}</code></td>
            </tr>
            """

        governance_rows = ""
        for label_key, field in [
            ("portfolio.platform.builder", "builder_status"),
            ("portfolio.platform.position_status", "position_status"),
            ("portfolio.platform.equity_status", "equity_status"),
            ("portfolio.platform.api", "api_status"),
            ("portfolio.platform.ui", "ui_status"),
        ]:
            governance_rows += f"""
            <tr>
                <td>{_e(_label(label_key))}</td>
                <td>{_e(_dto_label(governance.get(field)))}</td>
            </tr>
            """

        return f"""
        <section class="card">
            <h2>{_e(_label("portfolio.platform.title"))}</h2>
            <p>{_e(_label("portfolio.platform.subtitle"))}</p>
        </section>

        <section class="cards">
            <div class="card"><h3>{_e(_label("portfolio.platform.cash"))}</h3><p>{_e(ctx.formatter.number(summary.get("cash"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.positions_value"))}</h3><p>{_e(ctx.formatter.number(summary.get("positions_value"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.equity_value"))}</h3><p>{_e(ctx.formatter.number(summary.get("equity"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.total_pnl"))}</h3><p>{_e(ctx.formatter.number(summary.get("total_pnl"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.gross_exposure"))}</h3><p>{_e(ctx.formatter.number(summary.get("gross_exposure"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.net_exposure"))}</h3><p>{_e(ctx.formatter.number(summary.get("net_exposure"), 4))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.position_rows"))}</h3><p>{_e(summary.get("position_rows"))}</p></div>
            <div class="card"><h3>{_e(_label("portfolio.platform.open_position_rows"))}</h3><p>{_e(summary.get("open_position_rows"))}</p></div>
        </section>

        <section class="card">
            <h2>{_e(_label("portfolio.platform.positions"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("portfolio.platform.instrument"))}</th>
                        <th>{_e(_label("portfolio.platform.asset_class"))}</th>
                        <th>{_e(_label("portfolio.platform.quantity"))}</th>
                        <th>{_e(_label("portfolio.platform.avg_price"))}</th>
                        <th>{_e(_label("portfolio.platform.last_price"))}</th>
                        <th>{_e(_label("portfolio.platform.market_value"))}</th>
                        <th>{_e(_label("portfolio.platform.unrealized_pnl"))}</th>
                        <th>{_e(_label("portfolio.platform.realized_pnl"))}</th>
                        <th>{_e(_label("portfolio.platform.exposure"))}</th>
                        <th>{_e(_label("portfolio.platform.status"))}</th>
                    </tr>
                </thead>
                <tbody>{position_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("portfolio.platform.equity"))}</h2>
            <table>
                <tbody>
                    <tr><td>{_e(_label("portfolio.platform.cash"))}</td><td>{_e(ctx.formatter.number(equity.get("cash"), 4))}</td></tr>
                    <tr><td>{_e(_label("portfolio.platform.positions_value"))}</td><td>{_e(ctx.formatter.number(equity.get("positions_value"), 4))}</td></tr>
                    <tr><td>{_e(_label("portfolio.platform.equity_value"))}</td><td>{_e(ctx.formatter.number(equity.get("equity"), 4))}</td></tr>
                    <tr><td>{_e(_label("portfolio.platform.total_pnl"))}</td><td>{_e(ctx.formatter.number(equity.get("total_pnl"), 4))}</td></tr>
                    <tr><td>{_e(_label("portfolio.platform.gross_exposure"))}</td><td>{_e(ctx.formatter.number(equity.get("gross_exposure"), 4))}</td></tr>
                    <tr><td>{_e(_label("portfolio.platform.net_exposure"))}</td><td>{_e(ctx.formatter.number(equity.get("net_exposure"), 4))}</td></tr>
                </tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("portfolio.platform.configuration"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("portfolio.platform.portfolio_name"))}</th>
                        <th>{_e(_label("portfolio.platform.enabled"))}</th>
                        <th>{_e(_label("portfolio.platform.config"))}</th>
                    </tr>
                </thead>
                <tbody>{config_rows}</tbody>
            </table>
        </section>

        <section class="card">
            <h2>{_e(_label("portfolio.platform.governance"))}</h2>
            <table>
                <thead>
                    <tr>
                        <th>{_e(_label("portfolio.platform.governance"))}</th>
                        <th>{_e(_label("portfolio.platform.readiness"))}</th>
                    </tr>
                </thead>
                <tbody>{governance_rows}</tbody>
            </table>
        </section>
        """
