from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from decimal import Decimal

import psycopg2
import psycopg2.extras


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
TARGET_TRADES = 80
EARLY_STOP_MIN_TRADES = 20
MINIMUM_PROFIT_FACTOR = Decimal("1.15")
COST_BUFFER_MULTIPLIER = Decimal("1.50")
COHORT = "FRESH_V5_CONFIRM"


@dataclass(frozen=True)
class EvidenceKey:
    level: str
    scope: str
    timeframe: str
    strategy: str
    symbol: str = "*"
    side: str = "*"
    session: str = "*"
    regime: str = "*"
    exit_rule: str = "*"


@dataclass
class EvidenceStats:
    trades: int = 0
    net_pnl: Decimal = Decimal("0")
    gross_profit: Decimal = Decimal("0")
    gross_loss: Decimal = Decimal("0")
    absolute_gross_move: Decimal = Decimal("0")
    execution_cost: Decimal = Decimal("0")
    net_pnl_r: Decimal = Decimal("0")
    r_observations: int = 0

    def add(
        self, *, net_pnl: Decimal, gross_pnl: Decimal, commission: Decimal,
        realized_r: Decimal | None = None,
    ) -> None:
        self.trades += 1
        self.net_pnl += net_pnl
        self.absolute_gross_move += abs(gross_pnl)
        self.execution_cost += commission
        if net_pnl > 0:
            self.gross_profit += net_pnl
        elif net_pnl < 0:
            self.gross_loss += abs(net_pnl)
        if realized_r is not None:
            self.net_pnl_r += realized_r
            self.r_observations += 1


def classify(stats: EvidenceStats, *, exact: bool) -> tuple[str, str, Decimal, bool]:
    expectancy = stats.net_pnl / stats.trades if stats.trades else Decimal("0")
    observable = stats.gross_loss > 0
    profit_factor = stats.gross_profit / stats.gross_loss if observable else Decimal("0")
    average_move = stats.absolute_gross_move / stats.trades if stats.trades else Decimal("0")
    average_cost = stats.execution_cost / stats.trades if stats.trades else Decimal("0")
    costs_covered = average_move > average_cost * COST_BUFFER_MULTIPLIER

    if stats.trades < EARLY_STOP_MIN_TRADES:
        return "DISCOVERY_ONLY", "V5_HIERARCHICAL_SAMPLE_BELOW_20", profit_factor, observable
    if expectancy <= 0 and observable and profit_factor < Decimal("0.80"):
        return "EARLY_STOP", "V5_PERSISTENT_NEGATIVE_EXPECTANCY", profit_factor, observable
    if stats.trades < TARGET_TRADES:
        return "COLLECT", "V5_HIERARCHICAL_SAMPLE_BELOW_80", profit_factor, observable
    if not exact:
        return "COLLECT", "V5_HIERARCHY_SUPPORTS_EXACT_VALIDATION_ONLY", profit_factor, observable
    if not observable:
        return "COLLECT", "V5_PROFIT_FACTOR_NOT_OBSERVABLE", profit_factor, observable
    if not costs_covered:
        return "EARLY_STOP", "V5_EXECUTION_COST_BUFFER_NOT_COVERED", profit_factor, observable
    if expectancy <= 0:
        return "EARLY_STOP", "V5_NET_EXPECTANCY_NOT_POSITIVE", profit_factor, observable
    if profit_factor < MINIMUM_PROFIT_FACTOR:
        return "EARLY_STOP", "V5_PROFIT_FACTOR_BELOW_1_15", profit_factor, observable
    return "READY_FOR_OOS", "V5_EXACT_CONTEXT_COST_ADJUSTED_EDGE", profit_factor, observable


def evidence_priority_score(
    stats: EvidenceStats, *, decision: str, exact: bool
) -> Decimal:
    """Prioritize the cheapest next independent evidence, not small-sample PnL.

    Exact branches already carrying observations are more informative than a new
    one-trade branch.  A branch that survives the 20-trade early-stop gate remains
    the first collection priority until the immutable 80-trade OOS threshold.
    Supporting hierarchy levels can guide interpretation but must not outrank an
    exact branch in the runtime universe.
    """
    trades = max(0, int(stats.trades))
    if decision == "EARLY_STOP":
        return Decimal("-1000") + Decimal(trades)
    if not exact:
        return Decimal("10") + min(Decimal(trades), Decimal("80")) / Decimal("100")
    if decision == "READY_FOR_OOS":
        return Decimal("1000") + Decimal(trades)
    if trades >= EARLY_STOP_MIN_TRADES:
        return Decimal("600") + min(Decimal(trades), Decimal("79"))
    if trades >= 10:
        return Decimal("500") + Decimal(trades)
    if trades >= 5:
        return Decimal("400") + Decimal(trades)
    if trades >= 3:
        return Decimal("300") + Decimal(trades)
    return Decimal("100") + Decimal(trades)


def normalize_session(raw: str, compatibility: dict[tuple[str, str], str]) -> tuple[str, str]:
    value = str(raw or "UNKNOWN").strip().upper()
    if value in {"ВНЕ_ОСНОВНОЙ_СЕССИИ", "OFF_MAIN", "OUTSIDE_SESSION"}:
        exact = "OFF_MAIN"
    elif "ВЕЧЕР" in value or value == "EVENING":
        exact = "EVENING"
    elif "ОСНОВ" in value or value == "MAIN":
        exact = "MAIN"
    else:
        exact = value
    return exact, compatibility.get(("SESSION", exact), exact)


def normalize_regime(raw: str, compatibility: dict[tuple[str, str], str]) -> tuple[str, str]:
    exact = str(raw or "UNKNOWN").strip().upper()
    return exact, compatibility.get(("REGIME", exact), exact)


def evidence_timeframe(symbol: str, materialized: str, regime_timeframe: str) -> str:
    # public.closed_trades.timeframe may contain the transport marker LIVE.
    # V5 evidence follows the canonical closed-bar clock instead.
    normalized_symbol = str(symbol or "").upper()
    if normalized_symbol.startswith(("BR", "NG")) and normalized_symbol.endswith("@RTSX"):
        return "M1"
    regime = str(regime_timeframe or "").strip().upper()
    if regime in {"M1", "M5", "M15", "H1", "H4", "D1"}:
        return regime
    materialized_value = str(materialized or "").strip().upper()
    return materialized_value if materialized_value in {"M1", "M5", "M15", "H1", "H4", "D1"} else "UNKNOWN"


def evidence_id(key: EvidenceKey) -> str:
    raw = "|".join((COHORT,key.level,key.scope,key.timeframe,key.strategy,key.symbol,
                    key.side,key.session,key.regime,key.exit_rule))
    return "v5:" + hashlib.sha256(raw.encode()).hexdigest()


def main() -> int:
    groups: dict[EvidenceKey, EvidenceStats] = {}
    with psycopg2.connect(DB) as connection:
        with connection.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
            cursor.execute("""SELECT dimension_code,upper(raw_code) raw_code,compatible_group
                FROM analytics.evidence_compatibility_group_v1 WHERE enabled""")
            compatibility = {
                (row["dimension_code"], row["raw_code"]): row["compatible_group"]
                for row in cursor.fetchall()
            }
            cursor.execute("""
                SELECT portfolio_scope,symbol,upper(coalesce(side,'UNKNOWN')) side,
                       timeframe AS materialized_timeframe,
                       payload->'context'->>'regime_timeframe' AS regime_timeframe,
                       coalesce(nullif(strategy,''),'UNASSIGNED') strategy,
                       coalesce(payload->'context'->>'entry_session_msk','UNKNOWN') session,
                       coalesce(payload->'context'->>'entry_regime',entry_regime,'UNKNOWN') regime,
                       coalesce(payload->'context'->>'actual_exit_reason',
                                payload->'context'->>'exit_rule','UNKNOWN') exit_rule,
                       coalesce(net_pnl,0) net_pnl,coalesce(gross_pnl,0) gross_pnl,
                       coalesce(commission,0) commission,entry_price,abs(qty) qty,
                       nullif(payload->'context'->>'entry_stop_price','')::numeric entry_stop_price
                FROM analytics.closed_trades_fresh_v5_training_v1
            """)
            for row in cursor.fetchall():
                initial_risk = abs(
                    Decimal(str(row["entry_price"] or 0))
                    - Decimal(str(row["entry_stop_price"] or 0))
                ) * Decimal(str(row["qty"] or 0))
                realized_r = (
                    Decimal(str(row["net_pnl"])) / initial_risk
                    if row["entry_stop_price"] is not None and initial_risk > 0
                    else None
                )
                session, compatible_session = normalize_session(row["session"], compatibility)
                regime, compatible_regime = normalize_regime(row["regime"], compatibility)
                base = dict(scope=row["portfolio_scope"],
                            timeframe=evidence_timeframe(row["symbol"],row["materialized_timeframe"],row["regime_timeframe"]),
                            strategy=row["strategy"], side=row["side"])
                keys = (
                    EvidenceKey("STRATEGY", **base),
                    EvidenceKey("INSTRUMENT_SIDE", symbol=row["symbol"], **base),
                    EvidenceKey("COMPATIBLE_CONTEXT", symbol=row["symbol"],
                                session=compatible_session, regime=compatible_regime, **base),
                    EvidenceKey("EXACT_CONTEXT", symbol=row["symbol"], session=session,
                                regime=regime, exit_rule=row["exit_rule"], **base),
                )
                for key in keys:
                    groups.setdefault(key, EvidenceStats()).add(
                        net_pnl=Decimal(str(row["net_pnl"])),
                        gross_pnl=Decimal(str(row["gross_pnl"])),
                        commission=Decimal(str(row["commission"])),
                        realized_r=realized_r,
                    )

            cursor.execute("DELETE FROM analytics.hierarchical_evidence_v1 WHERE cohort_code=%s", (COHORT,))
            for key, stats in groups.items():
                decision, reason, profit_factor, observable = classify(
                    stats, exact=key.level == "EXACT_CONTEXT"
                )
                expectancy = stats.net_pnl / stats.trades
                cost_ratio = (stats.execution_cost / stats.absolute_gross_move
                              if stats.absolute_gross_move > 0 else Decimal("0"))
                priority = evidence_priority_score(
                    stats, decision=decision, exact=key.level == "EXACT_CONTEXT"
                )
                expectancy_r = (
                    stats.net_pnl_r / stats.r_observations
                    if stats.r_observations else None
                )
                cursor.execute("""
                    INSERT INTO analytics.hierarchical_evidence_v1(
                      evidence_key,cohort_code,level_code,scope_code,timeframe_code,
                      strategy_code,symbol_code,side_code,session_code,regime_code,exit_rule,
                      closed_trades,target_trades,net_pnl,expectancy,profit_factor,
                      profit_factor_observable,cost_ratio,priority_score,decision_code,reason_code,
                      net_pnl_r,expectancy_r,r_observable)
                    VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,80,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                """, (evidence_id(key),COHORT,key.level,key.scope,key.timeframe,key.strategy,
                      key.symbol,key.side,key.session,key.regime,key.exit_rule,stats.trades,
                      stats.net_pnl,expectancy,profit_factor,observable,cost_ratio,priority,
                      decision,reason,stats.net_pnl_r,expectancy_r,stats.r_observations==stats.trades))
    levels = {level: sum(1 for key in groups if key.level == level)
              for level in ("STRATEGY","INSTRUMENT_SIDE","COMPATIBLE_CONTEXT","EXACT_CONTEXT")}
    print(f"groups={len(groups)} levels={levels}")
    print("runtime_changed=0 execution_changed=0 orders_changed=0 fills_changed=0 live_allowed=0")
    print("VERDICT=V5_HIERARCHICAL_EVIDENCE_ROUTER_V1_OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
