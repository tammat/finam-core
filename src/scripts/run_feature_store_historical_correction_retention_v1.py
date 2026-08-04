from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

import psycopg2
import psycopg2.extras


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql:///finam_core",
)

ROOT = Path(__file__).resolve().parents[2]

POLICY_PATH = (
    ROOT
    / "config"
    / "runtime"
    / "feature_store_historical_correction_retention_v1.json"
)

SOURCE_VERSION = (
    "FEATURE_STORE_HISTORICAL_CORRECTION_RETENTION_V1"
)

AUDIT_TABLE = (
    "analytics."
    "feature_store_historical_correction_audit_v1"
)


def positive_int(value: Any, field_name: str) -> int:
    try:
        parsed = int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(
            f"{field_name} должен быть целым числом"
        ) from exc

    if parsed <= 0:
        raise ValueError(
            f"{field_name} должен быть больше нуля"
        )

    return parsed


def load_policy() -> dict[str, Any]:
    if not POLICY_PATH.exists():
        raise FileNotFoundError(
            f"Не найден retention policy: {POLICY_PATH}"
        )

    policy = json.loads(
        POLICY_PATH.read_text(encoding="utf-8")
    )

    required_fields = {
        "contract_version",
        "clean_retention_days",
        "detected_retention_days",
        "delete_batch_limit",
    }

    missing_fields = sorted(
        required_fields.difference(policy)
    )

    if missing_fields:
        raise ValueError(
            "В retention policy отсутствуют поля: "
            + ",".join(missing_fields)
        )

    if policy["contract_version"] != SOURCE_VERSION:
        raise ValueError(
            "Некорректная версия retention policy"
        )

    clean_days = positive_int(
        policy["clean_retention_days"],
        "clean_retention_days",
    )
    detected_days = positive_int(
        policy["detected_retention_days"],
        "detected_retention_days",
    )
    batch_limit = positive_int(
        policy["delete_batch_limit"],
        "delete_batch_limit",
    )

    if detected_days < clean_days:
        raise ValueError(
            "detected_retention_days не может быть "
            "меньше clean_retention_days"
        )

    return {
        "contract_version": policy["contract_version"],
        "clean_retention_days": clean_days,
        "detected_retention_days": detected_days,
        "delete_batch_limit": batch_limit,
    }


def ensure_contract(
    cur: psycopg2.extensions.cursor,
) -> None:
    cur.execute(
        """
        SELECT
            to_regclass(%s) AS audit_table,
            has_table_privilege(
                current_user,
                %s,
                'SELECT'
            ) AS can_select
        """,
        (
            AUDIT_TABLE,
            AUDIT_TABLE,
        ),
    )

    row = cur.fetchone()

    if not row or row["audit_table"] is None:
        raise RuntimeError(
            "Audit-таблица не существует"
        )

    if not row["can_select"]:
        raise PermissionError(
            "Текущая роль не имеет SELECT "
            "на audit-таблицу"
        )


def candidate_summary(
    cur: psycopg2.extensions.cursor,
    *,
    clean_days: int,
    detected_days: int,
) -> dict[str, int]:
    cur.execute(
        f"""
        SELECT
            count(*) FILTER (
                WHERE NOT correction_detected
                  AND created_at
                      < clock_timestamp()
                        - (%s * interval '1 day')
            )::bigint AS expired_clean_rows,

            count(*) FILTER (
                WHERE correction_detected
                  AND created_at
                      < clock_timestamp()
                        - (%s * interval '1 day')
            )::bigint AS expired_detected_rows,

            count(*)::bigint AS total_rows
        FROM {AUDIT_TABLE}
        """,
        (
            clean_days,
            detected_days,
        ),
    )

    row = cur.fetchone() or {}

    return {
        "expired_clean_rows": int(
            row.get("expired_clean_rows") or 0
        ),
        "expired_detected_rows": int(
            row.get("expired_detected_rows") or 0
        ),
        "total_rows": int(
            row.get("total_rows") or 0
        ),
    }


def delete_batch(
    cur: psycopg2.extensions.cursor,
    *,
    clean_days: int,
    detected_days: int,
    batch_limit: int,
) -> int:
    cur.execute(
        f"""
        WITH expired AS (
            SELECT audit_id
            FROM {AUDIT_TABLE}
            WHERE (
                    NOT correction_detected
                    AND created_at
                        < clock_timestamp()
                          - (%s * interval '1 day')
                  )
               OR (
                    correction_detected
                    AND created_at
                        < clock_timestamp()
                          - (%s * interval '1 day')
                  )
            ORDER BY created_at, audit_id
            LIMIT %s
            FOR UPDATE SKIP LOCKED
        ),
        deleted AS (
            DELETE FROM {AUDIT_TABLE} audit
            USING expired
            WHERE audit.audit_id = expired.audit_id
            RETURNING audit.audit_id
        )
        SELECT count(*)::integer AS deleted_rows
        FROM deleted
        """,
        (
            clean_days,
            detected_days,
            batch_limit,
        ),
    )

    row = cur.fetchone() or {}
    return int(row.get("deleted_rows") or 0)


def main() -> int:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--apply",
        action="store_true",
    )
    parser.add_argument(
        "--batch-limit",
        type=int,
        default=None,
    )

    args = parser.parse_args()
    policy = load_policy()

    batch_limit = (
        positive_int(
            args.batch_limit,
            "batch_limit",
        )
        if args.batch_limit is not None
        else policy["delete_batch_limit"]
    )

    dry_run = not args.apply

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cur:
            cur.execute(
                """
                SELECT pg_try_advisory_xact_lock(
                    hashtext(%s)
                ) AS acquired
                """,
                (SOURCE_VERSION,),
            )

            lock_row = cur.fetchone()

            if not lock_row or not lock_row["acquired"]:
                print("status=SKIPPED_ALREADY_RUNNING")
                print(
                    "VERDICT="
                    "FEATURE_STORE_HISTORICAL_CORRECTION_"
                    "RETENTION_V1_SKIPPED"
                )
                return 0

            ensure_contract(cur)

            before = candidate_summary(
                cur,
                clean_days=policy[
                    "clean_retention_days"
                ],
                detected_days=policy[
                    "detected_retention_days"
                ],
            )

            deleted_rows = 0

            if not dry_run:
                cur.execute(
                    """
                    SELECT has_table_privilege(
                        current_user,
                        %s,
                        'DELETE'
                    ) AS can_delete
                    """,
                    (AUDIT_TABLE,),
                )

                privilege_row = cur.fetchone()

                if (
                    not privilege_row
                    or not privilege_row["can_delete"]
                ):
                    raise PermissionError(
                        "Для --apply требуется DELETE "
                        "на audit-таблицу"
                    )

                deleted_rows = delete_batch(
                    cur,
                    clean_days=policy[
                        "clean_retention_days"
                    ],
                    detected_days=policy[
                        "detected_retention_days"
                    ],
                    batch_limit=batch_limit,
                )

            after = candidate_summary(
                cur,
                clean_days=policy[
                    "clean_retention_days"
                ],
                detected_days=policy[
                    "detected_retention_days"
                ],
            )

    print(
        "=== FEATURE_STORE_HISTORICAL_CORRECTION_"
        "RETENTION_V1 ==="
    )
    print(
        f"contract_version={policy['contract_version']}"
    )
    print(
        "clean_retention_days="
        f"{policy['clean_retention_days']}"
    )
    print(
        "detected_retention_days="
        f"{policy['detected_retention_days']}"
    )
    print(f"batch_limit={batch_limit}")
    print(
        "expired_clean_rows_before="
        f"{before['expired_clean_rows']}"
    )
    print(
        "expired_detected_rows_before="
        f"{before['expired_detected_rows']}"
    )
    print(f"total_rows_before={before['total_rows']}")
    print(f"deleted_rows={deleted_rows}")
    print(
        "expired_clean_rows_after="
        f"{after['expired_clean_rows']}"
    )
    print(
        "expired_detected_rows_after="
        f"{after['expired_detected_rows']}"
    )
    print(f"total_rows_after={after['total_rows']}")
    print(f"dry_run={int(dry_run)}")
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "FEATURE_STORE_HISTORICAL_CORRECTION_"
        "RETENTION_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
