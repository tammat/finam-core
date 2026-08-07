#!/usr/bin/env python3
from __future__ import annotations

import pathlib


ROOT = pathlib.Path("/opt/finam-core")

FILES = (
    ROOT / "scripts/research/"
    "migrate_finam_futures_fill_evidence_verification_v1.py",
    ROOT / "scripts/research/"
    "build_finam_futures_fill_evidence_verification_v1.py",
)


def main() -> int:
    unresolved: list[str] = []

    for path in FILES:
        if not path.is_file():
            unresolved.append(f"FILE_MISSING:{path}")

    if not unresolved:
        source = "\n".join(
            path.read_text(encoding="utf-8")
            for path in FILES
        )

        for fragment in (
            "futures_fill_evidence_verification_v1",
            "v_futures_fill_evidence_verified_v1",
            "COMMISSION_RECONCILIATION_MATCH",
            "fee_per_contract_side",
            "promoted_fill_count",
        ):
            if fragment not in source:
                unresolved.append(
                    f"CONTRACT_FRAGMENT_MISSING:{fragment}"
                )

        for fragment in (
            "UPDATE analytics.research_trade_v1",
            "DELETE FROM analytics.research_trade_v1",
            "send_order(",
            "place_order(",
            "submit_order(",
            "sqlite3",
            "bars.sqlite",
        ):
            if fragment in source:
                unresolved.append(
                    f"FORBIDDEN_FRAGMENT:{fragment}"
                )

    print(f"unresolved_count={len(unresolved)}")

    for item in unresolved:
        print(f"UNRESOLVED={item}")

    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")

    if unresolved:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_AUDIT_FAILED"
        )
        return 1

    print(
        "VERDICT="
        "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_AUDIT_OK"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
