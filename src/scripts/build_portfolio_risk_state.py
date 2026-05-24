from __future__ import annotations

import psycopg

from finam_core.analytics.statistics_repository import build_psycopg_url


def safe_float(v, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def classify_cluster(symbol: str) -> str:
    s = symbol.upper()

    if s.startswith("NG") or s.startswith("BR"):
        return "COMMODITIES"

    if "USD" in s or "RUB" in s:
        return "FX"

    return "EQUITIES"


def main() -> int:
    with psycopg.connect(build_psycopg_url()) as conn:
        with conn.cursor() as cur:

            cur.execute("""
                CREATE TABLE IF NOT EXISTS portfolio_risk_state (
                    id BIGSERIAL PRIMARY KEY,
                    cluster_name TEXT NOT NULL,
                    total_positions INTEGER NOT NULL,
                    total_heat NUMERIC NOT NULL,
                    avg_risk_multiplier NUMERIC NOT NULL,
                    max_risk_multiplier NUMERIC NOT NULL,
                    portfolio_share NUMERIC NOT NULL,
                    risk_state TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    calculated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    UNIQUE(cluster_name)
                );

                CREATE INDEX IF NOT EXISTS idx_portfolio_risk_state_cluster
                ON portfolio_risk_state(cluster_name);
            """)

            cur.execute("""
                SELECT
                    symbol,
                    capital_weight,
                    risk_multiplier,
                    allocator_decision
                FROM runtime_capital_allocator
            """)

            rows = cur.fetchall()

            clusters = {}

            total_heat = 0.0

            for row in rows:
                symbol, capital_weight, risk_multiplier, allocator_decision = row

                capital_weight = safe_float(capital_weight)
                risk_multiplier = safe_float(risk_multiplier)

                cluster = classify_cluster(symbol)

                if cluster not in clusters:
                    clusters[cluster] = {
                        "positions": 0,
                        "heat": 0.0,
                        "risk_sum": 0.0,
                        "max_risk": 0.0,
                    }

                clusters[cluster]["positions"] += 1
                clusters[cluster]["heat"] += capital_weight
                clusters[cluster]["risk_sum"] += risk_multiplier
                clusters[cluster]["max_risk"] = max(
                    clusters[cluster]["max_risk"],
                    risk_multiplier,
                )

                total_heat += capital_weight

            saved = 0

            for cluster_name, data in clusters.items():

                cluster_heat = float(data["heat"])

                portfolio_share = (
                    cluster_heat / total_heat
                    if total_heat > 0
                    else 0.0
                )

                avg_risk_multiplier = (
                    data["risk_sum"] / data["positions"]
                    if data["positions"] > 0
                    else 0.0
                )

                if portfolio_share >= 0.60:
                    risk_state = "OVEREXPOSED"
                elif portfolio_share >= 0.40:
                    risk_state = "ELEVATED"
                else:
                    risk_state = "NORMAL"

                reason = (
                    f"share={round(portfolio_share,4)} "
                    f"heat={round(cluster_heat,4)} "
                    f"positions={data['positions']} "
                    f"avg_risk={round(avg_risk_multiplier,4)}"
                )

                cur.execute("""
                    INSERT INTO portfolio_risk_state (
                        cluster_name,
                        total_positions,
                        total_heat,
                        avg_risk_multiplier,
                        max_risk_multiplier,
                        portfolio_share,
                        risk_state,
                        reason,
                        calculated_at
                    )
                    VALUES (
                        %s,%s,%s,%s,%s,%s,%s,%s,now()
                    )
                    ON CONFLICT(cluster_name)
                    DO UPDATE SET
                        total_positions=EXCLUDED.total_positions,
                        total_heat=EXCLUDED.total_heat,
                        avg_risk_multiplier=EXCLUDED.avg_risk_multiplier,
                        max_risk_multiplier=EXCLUDED.max_risk_multiplier,
                        portfolio_share=EXCLUDED.portfolio_share,
                        risk_state=EXCLUDED.risk_state,
                        reason=EXCLUDED.reason,
                        calculated_at=now()
                """, (
                    cluster_name,
                    data["positions"],
                    cluster_heat,
                    avg_risk_multiplier,
                    data["max_risk"],
                    portfolio_share,
                    risk_state,
                    reason,
                ))

                print(
                    "PORTFOLIO_RISK_STATE "
                    f"cluster={cluster_name} "
                    f"share={round(portfolio_share,4)} "
                    f"risk_state={risk_state} "
                    f"reason={reason}",
                    flush=True,
                )

                saved += 1

        conn.commit()

    print(
        f"PORTFOLIO_RISK_STATE_SUMMARY "
        f"clusters={saved} "
        f"total_heat={round(total_heat,4)}",
        flush=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
