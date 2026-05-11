# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import os
from typing import Any

import psycopg2


class OrderReconciliationLogger:
    def __init__(self, database_url: str | None = None) -> None:
        self.database_url = (database_url or os.getenv("DATABASE_URL") or "").strip()
        self.enabled = os.getenv("ORDER_RECONCILIATION_LOGGER_ENABLED", "1") == "1"

    def log_run(
        self,
        *,
        acks_count: int,
        broker_orders_count: int,
        issues: list,
        source: str = "order_ack_reconcile_timer",
        raw: dict[str, Any] | None = None,
    ) -> int | None:
        if not self.enabled or not self.database_url:
            return None

        status = "OK" if not issues else "ISSUES"

        try:
            with psycopg2.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        INSERT INTO order_reconciliation_runs
                            (acks_count, broker_orders_count, issues_count, status, source, raw)
                        VALUES
                            (%s, %s, %s, %s, %s, %s::jsonb)
                        RETURNING id
                        """,
                        (
                            int(acks_count),
                            int(broker_orders_count),
                            int(len(issues)),
                            status,
                            source,
                            json.dumps(raw or {}, ensure_ascii=False, default=str),
                        ),
                    )
                    run_id = int(cur.fetchone()[0])

                    for issue in issues:
                        cur.execute(
                            """
                            INSERT INTO order_reconciliation_issues
                                (run_id, order_id, symbol, issue_type, reason)
                            VALUES
                                (%s, %s, %s, %s, %s)
                            """,
                            (
                                run_id,
                                getattr(issue, "order_id", None),
                                str(getattr(issue, "symbol", "") or ""),
                                str(getattr(issue, "issue_type", "") or ""),
                                str(getattr(issue, "reason", "") or ""),
                            ),
                        )

                    return run_id
        except Exception as exc:
            print(f"ORDER_RECONCILIATION_LOG_FAILED error={exc}", flush=True)
            return None
