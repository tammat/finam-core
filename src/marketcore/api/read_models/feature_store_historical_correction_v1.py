from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Mapping, Sequence

import psycopg2
import psycopg2.extras


AUDIT_TABLE = (
    "analytics."
    "feature_store_historical_correction_audit_v1"
)

WATERMARK_TABLE = (
    "analytics."
    "feature_store_watermark_v1"
)

RETENTION_CONFIG_PATH = Path(
    "/opt/finam-core/config/runtime/"
    "feature_store_historical_correction_retention_v1.json"
)

SOURCE_VERSION = (
    "MARKETCORE_UI_HISTORICAL_CORRECTION_READ_MODEL_V1"
)

TIMESTAMP_CANDIDATES = (
    "created_at",
    "checked_at",
    "audited_at",
    "audit_ts",
    "updated_at",
)

AUDIT_ID_CANDIDATES = (
    "audit_run_id",
    "run_id",
    "build_id",
)

CHANGED_ROWS_CANDIDATES = (
    "changed_rows",
    "difference_rows",
)

DIRTY_UPDATED_CANDIDATES = (
    "dirty_rows_updated",
    "market_dirty_rows_updated",
)


@dataclass(frozen=True)
class TableContract:
    schema: str
    table: str
    columns: tuple[str, ...]
    timestamp_column: str | None


def _json_value(value: Any) -> Any:
    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, Decimal):
        return str(value)

    if isinstance(value, Mapping):
        return {
            str(key): _json_value(item)
            for key, item in value.items()
        }

    if isinstance(value, Sequence) and not isinstance(
        value,
        (str, bytes, bytearray),
    ):
        return [_json_value(item) for item in value]

    return value


def _first_existing(
    columns: Sequence[str],
    candidates: Sequence[str],
) -> str | None:
    available = set(columns)

    for candidate in candidates:
        if candidate in available:
            return candidate

    return None


def _load_table_contract(
    cur: psycopg2.extensions.cursor,
    *,
    schema: str,
    table: str,
) -> TableContract:
    cur.execute(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
          AND table_name = %s
        ORDER BY ordinal_position
        """,
        (schema, table),
    )

    columns = tuple(
        str(row["column_name"])
        for row in cur.fetchall()
    )

    if not columns:
        raise RuntimeError(
            f"table_contract_missing:{schema}.{table}"
        )

    return TableContract(
        schema=schema,
        table=table,
        columns=columns,
        timestamp_column=_first_existing(
            columns,
            TIMESTAMP_CANDIDATES,
        ),
    )


def _load_retention_policy() -> dict[str, Any]:
    if not RETENTION_CONFIG_PATH.exists():
        return {
            "status": "CONFIG_MISSING",
            "path": str(RETENTION_CONFIG_PATH),
        }

    payload = json.loads(
        RETENTION_CONFIG_PATH.read_text(
            encoding="utf-8",
        )
    )

    if not isinstance(payload, dict):
        raise RuntimeError(
            "retention_config_not_object"
        )

    return {
        "status": "READY",
        "path": str(RETENTION_CONFIG_PATH),
        "contract_version": payload.get(
            "contract_version"
        ),
        "clean_retention_days": payload.get(
            "clean_retention_days"
        ),
        "detected_retention_days": payload.get(
            "detected_retention_days"
        ),
        "delete_batch_limit": payload.get(
            "delete_batch_limit"
        ),
    }


def _load_recent_audits(
    cur: psycopg2.extensions.cursor,
    contract: TableContract,
    *,
    limit: int,
) -> list[dict[str, Any]]:
    order_sql = ""

    if contract.timestamp_column:
        order_sql = (
            f' ORDER BY "{contract.timestamp_column}" DESC'
        )

    cur.execute(
        f"""
        SELECT to_jsonb(a) AS audit_row
        FROM {AUDIT_TABLE} AS a
        {order_sql}
        LIMIT %s
        """,
        (limit,),
    )

    return [
        _json_value(dict(row["audit_row"]))
        for row in cur.fetchall()
    ]


def _sum_candidate(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
) -> int:
    total = 0

    for row in rows:
        for candidate in candidates:
            if candidate not in row:
                continue

            value = row.get(candidate)

            try:
                total += int(value or 0)
            except (TypeError, ValueError):
                pass

            break

    return total


def _count_changed_pairs(
    rows: Sequence[Mapping[str, Any]],
) -> int:
    """
    Считает уникальные затронутые пары symbol/timeframe.

    Audit-таблица хранит одну строку на пару, поэтому changed_pairs
    нельзя получать суммированием несуществующей колонки.
    """
    changed_pairs: set[tuple[str, str]] = set()

    for row in rows:
        correction_detected = bool(
            row.get("correction_detected")
        )

        try:
            changed_rows = int(
                row.get("changed_rows") or 0
            )
        except (TypeError, ValueError):
            changed_rows = 0

        if not correction_detected and changed_rows <= 0:
            continue

        symbol = str(row.get("symbol") or "").strip()
        timeframe = str(
            row.get("timeframe") or ""
        ).strip()

        if not symbol or not timeframe:
            continue

        changed_pairs.add(
            (symbol, timeframe)
        )

    return len(changed_pairs)


def _latest_candidate(
    rows: Sequence[Mapping[str, Any]],
    candidates: Sequence[str],
) -> Any:
    if not rows:
        return None

    row = rows[0]

    for candidate in candidates:
        if candidate in row:
            return _json_value(row.get(candidate))

    return None


def _load_watermark_summary(
    cur: psycopg2.extensions.cursor,
) -> dict[str, Any]:
    cur.execute(
        f"""
        SELECT
            count(*) AS rows,
            count(*) FILTER (
                WHERE market_dirty
            ) AS dirty_rows,
            count(*) FILTER (
                WHERE market_snapshot_last_ts
                   IS DISTINCT FROM
                      feature_snapshot_last_ts
            ) AS watermark_lag,
            max(market_dirty_at)
                AS last_market_dirty_at,
            max(feature_processed_at)
                AS last_feature_processed_at,
            max(market_snapshot_last_ts)
                AS max_market_snapshot_last_ts,
            max(feature_snapshot_last_ts)
                AS max_feature_snapshot_last_ts
        FROM {WATERMARK_TABLE}
        """
    )

    row = dict(cur.fetchone())

    return _json_value(row)


def build_read_model(
    dsn: str,
    *,
    audit_limit: int = 50,
) -> dict[str, Any]:
    if audit_limit < 1 or audit_limit > 500:
        raise ValueError(
            "audit_limit_out_of_range"
        )

    with psycopg2.connect(dsn) as conn:
        conn.set_session(
            readonly=True,
            autocommit=False,
        )

        with conn.cursor(
            cursor_factory=
                psycopg2.extras.RealDictCursor
        ) as cur:
            audit_contract = _load_table_contract(
                cur,
                schema="analytics",
                table=(
                    "feature_store_"
                    "historical_correction_audit_v1"
                ),
            )

            watermark_contract = _load_table_contract(
                cur,
                schema="analytics",
                table="feature_store_watermark_v1",
            )

            recent_audits = _load_recent_audits(
                cur,
                audit_contract,
                limit=audit_limit,
            )

            watermark = _load_watermark_summary(cur)

    changed_rows = _sum_candidate(
        recent_audits,
        CHANGED_ROWS_CANDIDATES,
    )

    changed_pairs = _count_changed_pairs(
        recent_audits,
    )

    dirty_rows_updated = _sum_candidate(
        recent_audits,
        DIRTY_UPDATED_CANDIDATES,
    )

    dirty_rows = int(
        watermark.get("dirty_rows") or 0
    )

    watermark_lag = int(
        watermark.get("watermark_lag") or 0
    )

    overall_status = "READY"

    if dirty_rows > 0 or watermark_lag > 0:
        overall_status = "ATTENTION"

    return {
        "contract_version": SOURCE_VERSION,
        "status": overall_status,
        "read_only": True,
        "generated_at": (
            datetime.now().astimezone().isoformat()
        ),
        "summary": {
            "audit_rows_loaded": len(recent_audits),
            "changed_rows": changed_rows,
            "changed_pairs": changed_pairs,
            "dirty_rows_updated": dirty_rows_updated,
            "current_dirty_rows": dirty_rows,
            "watermark_lag": watermark_lag,
            "latest_audit_run_id": _latest_candidate(
                recent_audits,
                AUDIT_ID_CANDIDATES,
            ),
            "latest_audit_ts": (
                recent_audits[0].get(
                    audit_contract.timestamp_column
                )
                if recent_audits
                and audit_contract.timestamp_column
                else None
            ),
        },
        "watermark": watermark,
        "retention": _load_retention_policy(),
        "recent_audits": recent_audits,
        "contracts": {
            "audit_table": {
                "name": AUDIT_TABLE,
                "columns": list(
                    audit_contract.columns
                ),
                "timestamp_column": (
                    audit_contract.timestamp_column
                ),
            },
            "watermark_table": {
                "name": WATERMARK_TABLE,
                "columns": list(
                    watermark_contract.columns
                ),
            },
        },
        "safety": {
            "direct_sql_from_page_allowed": False,
            "write_actions_allowed": False,
            "systemctl_actions_allowed": False,
            "runtime_changed": 0,
            "execution_changed": 0,
            "orders_changed": 0,
            "fills_changed": 0,
            "micro_live_allowed": 0,
        },
    }
