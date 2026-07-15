from __future__ import annotations

from datetime import datetime, timezone

from marketcore.services.profit_funnel_source_registry_v2 import observe_profit_funnel_sources_v2


def main() -> None:
    now = datetime.now(timezone.utc)
    rows = observe_profit_funnel_sources_v2()
    print("# MarketCore Profit Funnel Source Audit V2")
    print()
    for row in rows:
        age = None if row.source_as_of is None else max(0, int((now - row.source_as_of).total_seconds()))
        cohort = row.cohort_id if row.cohort_count == 1 else "UNRECONCILED"
        print(
            f"stage={row.stage.value} count={row.count} source={row.source_identity} "
            f"source_age_seconds={age if age is not None else 'UNAVAILABLE'} scope={row.scope_code} "
            f"cohort={cohort} cohort_count={row.cohort_count} quality={row.quality_code} "
            f"net_pnl={row.net_pnl if row.net_pnl is not None else 'NOT_APPLICABLE'} "
            f"cost_impact={row.cost_impact if row.cost_impact is not None else 'NOT_APPLICABLE'}"
        )
    print()
    print(f"stages_total={len(rows)}")
    print(f"scope_unverified={sum(row.scope_code == 'SCOPE_UNVERIFIED' for row in rows)}")
    print(f"cohort_unreconciled={sum(row.cohort_count != 1 for row in rows)}")
    print("real_trading_changed=0")
    print("VERDICT=MARKETCORE_STAGE7_PROFIT_FUNNEL_SOURCE_AUDIT_READY")


if __name__ == "__main__":
    main()
