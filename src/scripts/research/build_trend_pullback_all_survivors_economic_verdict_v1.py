from decimal import Decimal


rows = (
    {
        "symbol": "NVTK@MISX",
        "net_pf": Decimal(
            "0.5792414016645327574226393779"
        ),
        "net_expectancy": Decimal(
            "-0.6770240676496097137901127493"
        ),
    },
    {
        "symbol": "PLZL@MISX",
        "net_pf": Decimal(
            "0.6956272674627637411832152308"
        ),
        "net_expectancy": Decimal(
            "-0.9126494201605709188224799286"
        ),
    },
    {
        "symbol": "USDRUBF@RTSX",
        "net_pf": Decimal(
            "0.9961603973135745898227554454"
        ),
        "net_expectancy": Decimal(
            "-0.1296207046249514185775359503"
        ),
    },
)

survivors = 0

for row in rows:
    survive = (
        row["net_pf"] > Decimal("1")
        and row["net_expectancy"] > Decimal("0")
    )

    survivors += int(survive)

    status = (
        "SURVIVE_AFTER_BASE_COSTS"
        if survive
        else "REJECT_AFTER_BASE_COSTS"
    )

    print(
        "ECONOMIC_VERDICT_ROW "
        f"symbol={row['symbol']} "
        f"net_profit_factor={row['net_pf']} "
        f"net_expectancy={row['net_expectancy']} "
        f"status={status}"
    )

print(f"gross_robust_symbols={len(rows)}")
print(f"economic_survivors={survivors}")

if survivors != 0:
    raise SystemExit(
        "ERROR=EXPECTED_ZERO_ECONOMIC_SURVIVORS"
    )

print("economic_edge_claimed=0")
print("micro_live_allowed=0")
print(
    "VERDICT="
    "TREND_PULLBACK_ALL_ROBUST_SURVIVORS_REJECTED_V1"
)
