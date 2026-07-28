from __future__ import annotations

import math
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from finam_core.analytics.statistics_repository import build_psycopg_url


@dataclass(frozen=True)
class PortfolioRiskDecision:
    allowed: bool
    cluster_name: str
    risk_state: str
    reason: str
    decision_code: str
    decision_id: str
    process_id: str
    requested_quantity: float
    approved_quantity: float


class PortfolioRiskGate:
    """Fail-closed, DB-audited portfolio risk admission gate."""

    def __init__(self, dsn: str | None = None) -> None:
        self.dsn = dsn or build_psycopg_url()

    def classify_cluster(self, symbol: str) -> str:
        s = symbol.upper()
        if s.startswith(("NG", "BR")):
            return "COMMODITIES"
        if s.startswith(("GD", "GLD")) or "GOLD" in s:
            return "METALS"
        if any(code in s for code in ("USD", "RUB", "CNY")):
            return "FX"
        return "EQUITIES"

    @staticmethod
    def _process_id(signal_id: Any, symbol: str, strategy_family: str) -> uuid.UUID:
        try:
            return uuid.UUID(str(signal_id))
        except (TypeError, ValueError, AttributeError):
            return uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"marketcore:risk:{signal_id or 'missing'}:{symbol}:{strategy_family}",
            )

    def check(
        self,
        symbol: str,
        *,
        signal_id: Any = None,
        strategy_family: str = "UNKNOWN",
        requested_quantity: float = 0.0,
        gross_exposure_rub: float = 0.0,
        symbol_exposure_rub: float = 0.0,
        used_margin_rub: float = 0.0,
        equity_rub: float = 0.0,
        peak_equity_rub: float = 0.0,
        daily_pnl_rub: float = 0.0,
        drawdown_rub: float = 0.0,
        spread_bps: float | None = None,
        book_depth: float | None = None,
        quote_observed_at: datetime | None = None,
        entry_price: float = 0.0,
        stop_price: float = 0.0,
        contract_multiplier: float = 1.0,
    ) -> PortfolioRiskDecision:
        cluster = self.classify_cluster(symbol)
        decision_id = uuid.uuid4()
        process_id = self._process_id(signal_id, symbol, strategy_family)
        requested = max(0.0, float(requested_quantity or 0.0))
        now = datetime.now(timezone.utc)

        with psycopg.connect(self.dsn) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT enabled, max_portfolio_share,
                           elevated_reduction_factor, max_state_age_seconds,
                           max_daily_loss_pct, max_drawdown_pct,
                           max_symbol_share, max_gross_exposure_pct,
                           max_margin_utilization, max_risk_per_trade_pct
                    FROM analytics.risk_config_v2
                    WHERE policy_key = 'DEFAULT'
                    """
                )
                config = cur.fetchone()

                state_row = None
                degradation_row = None
                if config:
                    cur.execute(
                        """
                        SELECT risk_state, portfolio_share, reason, calculated_at
                        FROM public.portfolio_risk_state
                        WHERE cluster_name = %s
                        ORDER BY calculated_at DESC
                        LIMIT 1
                        """,
                        (cluster,),
                    )
                    state_row = cur.fetchone()
                    cur.execute(
                        """
                        SELECT sample_size, expectancy_rub, profit_factor, status,
                               scale_factor, reason, calculated_at
                        FROM analytics.strategy_degradation_state_v1
                        WHERE strategy_family = %s
                        """,
                        (strategy_family,),
                    )
                    degradation_row = cur.fetchone()

                code = "BLOCK"
                risk_state = "UNKNOWN"
                reason = "risk_policy_missing"
                approved = 0.0
                policy_snapshot: dict[str, Any] = {"policy_key": "DEFAULT"}

                if config:
                    (enabled, max_share, reduction_factor, max_age_seconds,
                     max_daily_loss_pct, max_drawdown_pct, max_symbol_share,
                     max_gross_exposure_pct, max_margin_utilization,
                     max_risk_per_trade_pct) = config
                    max_share = float(max_share)
                    reduction_factor = float(reduction_factor)
                    max_age_seconds = int(max_age_seconds)
                    policy_snapshot.update(
                        enabled=bool(enabled),
                        max_portfolio_share=max_share,
                        elevated_reduction_factor=reduction_factor,
                        max_state_age_seconds=max_age_seconds,
                        max_daily_loss_pct=float(max_daily_loss_pct),
                        max_drawdown_pct=float(max_drawdown_pct),
                        max_symbol_share=float(max_symbol_share),
                        max_gross_exposure_pct=float(max_gross_exposure_pct),
                        max_margin_utilization=float(max_margin_utilization),
                        max_risk_per_trade_pct=float(max_risk_per_trade_pct),
                    )
                    if not enabled:
                        reason = "risk_policy_disabled"
                    elif equity_rub <= 0:
                        reason = "portfolio_equity_missing"
                    elif daily_pnl_rub <= -(equity_rub * float(max_daily_loss_pct)):
                        reason = "daily_loss_limit_exceeded"
                    elif peak_equity_rub > 0 and drawdown_rub / peak_equity_rub >= float(max_drawdown_pct):
                        reason = "drawdown_limit_exceeded"
                    elif symbol_exposure_rub / equity_rub > float(max_symbol_share):
                        reason = "symbol_exposure_limit_exceeded"
                    elif gross_exposure_rub / equity_rub > float(max_gross_exposure_pct):
                        reason = "gross_exposure_limit_exceeded"
                    elif used_margin_rub / equity_rub > float(max_margin_utilization):
                        reason = "margin_utilization_limit_exceeded"
                    elif not state_row:
                        reason = "portfolio_risk_state_missing"
                    else:
                        risk_state, portfolio_share, state_reason, calculated_at = state_row
                        share = float(portfolio_share or 0.0)
                        age_seconds = max(0.0, (now - calculated_at).total_seconds())
                        policy_snapshot.update(
                            portfolio_share=share,
                            state_reason=state_reason,
                            state_age_seconds=age_seconds,
                        )
                        entry = float(entry_price or 0.0)
                        stop = float(stop_price or 0.0)
                        multiplier = float(contract_multiplier or 0.0)
                        risk_per_contract = abs(entry - stop) * multiplier
                        risk_budget = equity_rub * float(max_risk_per_trade_pct)
                        unit_exposure = entry * multiplier
                        policy_snapshot.update(
                            entry_price=entry,
                            stop_price=stop,
                            contract_multiplier=multiplier,
                            risk_budget_rub=risk_budget,
                            risk_per_contract_rub=risk_per_contract,
                        )
                        if age_seconds > max_age_seconds:
                            reason = f"portfolio_risk_state_stale age={age_seconds:.0f}s"
                        elif str(risk_state).upper() == "OVEREXPOSED" or share > max_share:
                            reason = f"portfolio_cluster_overexposed share={share:.4f}"
                        elif requested <= 0:
                            reason = "requested_quantity_missing"
                        elif entry <= 0 or stop <= 0 or multiplier <= 0 or risk_per_contract <= 0:
                            reason = "position_risk_inputs_missing"
                        else:
                            qty_risk = math.floor(risk_budget / risk_per_contract)
                            qty_symbol = math.floor(max(
                                0.0,
                                equity_rub * float(max_symbol_share) - symbol_exposure_rub,
                            ) / unit_exposure)
                            qty_cluster = math.floor(max(
                                0.0,
                                equity_rub * max_share - share * equity_rub,
                            ) / unit_exposure)
                            degradation_status = "UNASSESSED"
                            degradation_scale = 1.0
                            if degradation_row:
                                (_sample, _expectancy, _pf, degradation_status,
                                 degradation_scale, degradation_reason, degradation_at) = degradation_row
                                degradation_status = str(degradation_status).upper()
                                degradation_scale = float(degradation_scale or 0.0)
                                policy_snapshot.update(
                                    degradation_status=degradation_status,
                                    degradation_reason=degradation_reason,
                                    degradation_calculated_at=str(degradation_at),
                                )
                            if degradation_status == "BLOCKED":
                                reason = "strategy_degradation_blocked"
                            else:
                                qty_degradation = requested
                                if degradation_status == "ELEVATED":
                                    qty_degradation = max(1, math.floor(requested * degradation_scale))
                                elif degradation_status == "UNASSESSED":
                                    qty_degradation = min(requested, 1.0)
                                if str(risk_state).upper() == "ELEVATED":
                                    qty_degradation = min(
                                        qty_degradation,
                                        max(1, math.floor(requested * reduction_factor)),
                                    )
                                approved = max(0.0, min(
                                    requested, qty_risk, qty_symbol,
                                    qty_cluster, qty_degradation,
                                ))
                                projected_cluster_share = share + approved * unit_exposure / equity_rub
                                policy_snapshot.update(
                                    quantity_by_risk=qty_risk,
                                    quantity_by_symbol=qty_symbol,
                                    quantity_by_cluster=qty_cluster,
                                    quantity_by_degradation=qty_degradation,
                                    projected_cluster_share=projected_cluster_share,
                                )
                                if approved <= 0:
                                    reason = "projected_risk_capacity_exhausted"
                                elif approved < requested:
                                    code = "REDUCE"
                                    reason = f"projected_risk_reduced={approved:g}/{requested:g}"
                                else:
                                    code = "ALLOW"
                                    reason = f"portfolio_risk_ok projected_share={projected_cluster_share:.4f}"

                cur.execute(
                    """
                    INSERT INTO analytics.risk_control_decision_v2 (
                        decision_id, process_id, symbol, strategy_family,
                        decision_code, reason_codes, requested_quantity,
                        approved_quantity, gross_exposure_rub, daily_pnl_rub,
                        drawdown_rub, spread_bps, book_depth, quote_observed_at,
                        symbol_exposure_rub, used_margin_rub, equity_rub, peak_equity_rub,
                        risk_budget_rub, risk_per_contract_rub, entry_price, stop_price,
                        contract_multiplier, projected_cluster_share, degradation_status,
                        policy_snapshot
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                    """,
                    (
                        decision_id,
                        process_id,
                        symbol,
                        strategy_family,
                        code,
                        Jsonb([reason]),
                        requested,
                        approved,
                        gross_exposure_rub,
                        daily_pnl_rub,
                        drawdown_rub,
                        spread_bps,
                        book_depth,
                        quote_observed_at,
                        symbol_exposure_rub,
                        used_margin_rub,
                        equity_rub,
                        peak_equity_rub,
                        policy_snapshot.get("risk_budget_rub"),
                        policy_snapshot.get("risk_per_contract_rub"),
                        policy_snapshot.get("entry_price"),
                        policy_snapshot.get("stop_price"),
                        policy_snapshot.get("contract_multiplier"),
                        policy_snapshot.get("projected_cluster_share"),
                        policy_snapshot.get("degradation_status", "UNASSESSED"),
                        Jsonb(policy_snapshot),
                    ),
                )

        return PortfolioRiskDecision(
            allowed=code in {"ALLOW", "REDUCE"} and approved > 0,
            cluster_name=cluster,
            risk_state=str(risk_state),
            reason=reason,
            decision_code=code,
            decision_id=str(decision_id),
            process_id=str(process_id),
            requested_quantity=requested,
            approved_quantity=approved,
        )
