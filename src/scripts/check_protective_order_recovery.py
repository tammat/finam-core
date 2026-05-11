# -*- coding: utf-8 -*-
from __future__ import annotations

import os
from dotenv import load_dotenv

from finam_core.reconciliation.protective_order_recovery_check import ProtectiveOrderRecoveryCheck

load_dotenv(os.getenv("FINAM_ENV_FILE", "/opt/finam-core/deploy/env/.env"), override=False)


def main() -> int:
    limit = int(os.getenv("PROTECTIVE_ORDER_RECOVERY_LIMIT", "100"))
    issues = ProtectiveOrderRecoveryCheck().check(limit=limit)

    print("PROTECTIVE_ORDER_RECOVERY_CHECK")
    print(f"issues={len(issues)}")

    for issue in issues:
        print(
            f"PROTECTIVE_ORDER_RECOVERY_ISSUE "
            f"type={issue.issue_type} symbol={issue.symbol} side={issue.side} "
            f"qty={issue.qty} entry_order_id={issue.entry_order_id} reason={issue.reason}"
        )

    return 1 if issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
