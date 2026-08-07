#!/usr/bin/env python3
from __future__ import annotations

import argparse
from decimal import Decimal
from typing import Any

import psycopg2
from psycopg2.extras import RealDictCursor

from finam_core.analytics.statistics_repository import build_psycopg_url


DEFAULT_FEE_PER_CONTRACT_SIDE = Decimal("0.45")
DEFAULT_COMMISSION_ACCOUNT = "DEFAULT"
TOLERANCE = Decimal("0.000001")


def dec(value: Any) -> Decimal:
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Finam Futures Fill Evidence Verification V1"
    )
    parser.add_argument("--source-version", required=True)
    parser.add_argument("--verification-batch-id", required=True)
    parser.add_argument(
        "--fee-per-contract-side",
        type=Decimal,
        default=DEFAULT_FEE_PER_CONTRACT_SIDE,
    )
    parser.add_argument(
        "--commission-account",
        default=DEFAULT_COMMISSION_ACCOUNT,
    )
    parser.add_argument("--date-from")
    parser.add_argument("--date-to")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    if args.fee_per_contract_side <= 0:
        raise SystemExit(
            "ERROR=fee_per_contract_side_must_be_positive"
        )

    verification_rows: list[dict[str, Any]] = []
    unresolved: list[str] = []

    with psycopg2.connect(build_psycopg_url()) as conn:
        with conn.cursor(
            cursor_factory=RealDictCursor,
        ) as cur:
            cur.execute(
                """
                SELECT
                    min(trade_date) AS first_commission_date,
                    max(trade_date) AS last_commission_date,
                    count(*)::integer AS commission_day_count
                FROM analytics.futures_commission_daily_v1
                WHERE broker_account = %s
                  AND (%s::date IS NULL OR trade_date >= %s::date)
                  AND (%s::date IS NULL OR trade_date <= %s::date)
                  AND evidence_status = 'VERIFIED'
                """,
                (
                    args.commission_account,
                    args.date_from,
                    args.date_from,
                    args.date_to,
                    args.date_to,
                ),
            )
            coverage = dict(cur.fetchone())

            if int(coverage["commission_day_count"] or 0) == 0:
                raise SystemExit(
                    "ERROR=verified_commission_rows_missing:"
                    f"{args.commission_account}"
                )

            first_date = coverage["first_commission_date"]
            last_date = coverage["last_commission_date"]

            cur.execute(
                """
                SELECT
                    f.trade_date,
                    f.broker_account AS fill_broker_account,
                    count(*)::integer AS fill_row_count,
                    sum(f.quantity_contracts)::numeric
                        AS contract_sides,
                    count(*) FILTER (
                        WHERE f.evidence_status = 'REVIEW_REQUIRED'
                    )::integer AS review_required_count,
                    count(*) FILTER (
                        WHERE f.evidence_status = 'VERIFIED'
                    )::integer AS already_verified_count,
                    d.broker_account AS commission_broker_account,
                    d.commission_total::numeric
                        AS reported_commission,
                    d.source_document AS commission_source_document,
                    d.source_reference AS commission_source_reference,
                    d.source_version AS commission_source_version
                FROM analytics.futures_fill_evidence_v1 f
                JOIN analytics.futures_commission_daily_v1 d
                  ON d.trade_date = f.trade_date
                 AND d.broker_account = %s
                 AND d.evidence_status = 'VERIFIED'
                WHERE f.source_version = %s
                  AND f.trade_date >= %s
                  AND f.trade_date <= %s
                  AND (%s::date IS NULL OR f.trade_date >= %s::date)
                  AND (%s::date IS NULL OR f.trade_date <= %s::date)
                GROUP BY
                    f.trade_date,
                    f.broker_account,
                    d.broker_account,
                    d.commission_total,
                    d.source_document,
                    d.source_reference,
                    d.source_version
                ORDER BY
                    f.trade_date,
                    f.broker_account
                """,
                (
                    args.commission_account,
                    args.source_version,
                    first_date,
                    last_date,
                    args.date_from,
                    args.date_from,
                    args.date_to,
                    args.date_to,
                ),
            )

            source_rows = [
                dict(row)
                for row in cur.fetchall()
            ]

            if not source_rows:
                raise SystemExit(
                    "ERROR=source_fill_rows_missing_in_commission_period"
                )

            for source in source_rows:
                contract_sides = dec(source["contract_sides"])
                calculated = (
                    contract_sides
                    * args.fee_per_contract_side
                )
                reported = dec(source["reported_commission"])
                delta = calculated - reported

                status = (
                    "MATCH"
                    if abs(delta) <= TOLERANCE
                    else "MISMATCH"
                )

                if status != "MATCH":
                    unresolved.append(
                        "COMMISSION_MISMATCH:"
                        f"{source['trade_date']}:"
                        f"{source['fill_broker_account']}:"
                        f"{delta}"
                    )

                verification_rows.append(
                    {
                        **source,
                        "calculated_commission": calculated,
                        "reconciliation_delta": delta,
                        "reconciliation_status": status,
                    }
                )

            cur.execute(
                """
                SELECT
                    count(*)::integer AS outside_period_fill_count,
                    min(trade_date) AS outside_first_date,
                    max(trade_date) AS outside_last_date
                FROM analytics.futures_fill_evidence_v1
                WHERE source_version = %s
                  AND (
                      trade_date < %s
                      OR trade_date > %s
                  )
                """,
                (
                    args.source_version,
                    first_date,
                    last_date,
                ),
            )
            outside = dict(cur.fetchone())

            promoted_count = 0

            if args.apply and not unresolved:
                cur.execute(
                    """
                    UPDATE analytics.futures_fill_evidence_v1 f
                    SET evidence_status = 'VERIFIED'
                    WHERE f.source_version = %s
                      AND f.evidence_status = 'REVIEW_REQUIRED'
                      AND f.trade_date >= %s
                      AND f.trade_date <= %s
                      AND (%s::date IS NULL OR f.trade_date >= %s::date)
                      AND (%s::date IS NULL OR f.trade_date <= %s::date)
                      AND EXISTS (
                          SELECT 1
                          FROM analytics.futures_commission_daily_v1 d
                          WHERE d.trade_date = f.trade_date
                            AND d.broker_account = %s
                            AND d.evidence_status = 'VERIFIED'
                            AND abs(
                                d.commission_total
                                - (
                                    SELECT
                                        sum(x.quantity_contracts)
                                        * %s::numeric
                                    FROM
                                        analytics.futures_fill_evidence_v1 x
                                    WHERE
                                        x.source_version = f.source_version
                                        AND x.trade_date = f.trade_date
                                        AND x.broker_account =
                                            f.broker_account
                                )
                            ) <= %s::numeric
                      )
                    """,
                    (
                        args.source_version,
                        first_date,
                        last_date,
                        args.date_from,
                        args.date_from,
                        args.date_to,
                        args.date_to,
                        args.commission_account,
                        args.fee_per_contract_side,
                        TOLERANCE,
                    ),
                )
                promoted_count = cur.rowcount

                for row in verification_rows:
                    cur.execute(
                        """
                        INSERT INTO
                        analytics.futures_fill_evidence_verification_v1 (
                            verification_batch_id,
                            source_version,
                            trade_date,
                            broker_account,
                            fill_row_count,
                            contract_sides,
                            fee_per_contract_side,
                            calculated_commission,
                            reported_commission,
                            reconciliation_delta,
                            reconciliation_status,
                            reviewed_fill_count,
                            verified_fill_count,
                            verification_reason
                        )
                        VALUES (
                            %s, %s, %s, %s, %s, %s, %s,
                            %s, %s, %s, %s, %s, %s, %s
                        )
                        ON CONFLICT (
                            verification_batch_id,
                            source_version,
                            trade_date,
                            broker_account
                        )
                        DO UPDATE SET
                            fill_row_count =
                                EXCLUDED.fill_row_count,
                            contract_sides =
                                EXCLUDED.contract_sides,
                            fee_per_contract_side =
                                EXCLUDED.fee_per_contract_side,
                            calculated_commission =
                                EXCLUDED.calculated_commission,
                            reported_commission =
                                EXCLUDED.reported_commission,
                            reconciliation_delta =
                                EXCLUDED.reconciliation_delta,
                            reconciliation_status =
                                EXCLUDED.reconciliation_status,
                            reviewed_fill_count =
                                EXCLUDED.reviewed_fill_count,
                            verified_fill_count =
                                EXCLUDED.verified_fill_count,
                            verification_reason =
                                EXCLUDED.verification_reason
                        """,
                        (
                            args.verification_batch_id,
                            args.source_version,
                            row["trade_date"],
                            row["fill_broker_account"],
                            row["fill_row_count"],
                            row["contract_sides"],
                            args.fee_per_contract_side,
                            row["calculated_commission"],
                            row["reported_commission"],
                            row["reconciliation_delta"],
                            row["reconciliation_status"],
                            row["review_required_count"],
                            (
                                int(row["already_verified_count"])
                                + int(row["review_required_count"])
                            ),
                            (
                                "COMMISSION_RECONCILIATION_MATCH:"
                                f"{row['commission_broker_account']}:"
                                f"{row['commission_source_version']}"
                            ),
                        ),
                    )

    matched_count = sum(
        row["reconciliation_status"] == "MATCH"
        for row in verification_rows
    )

    print("=== FINAM FUTURES FILL EVIDENCE VERIFICATION V1 ===")
    print(f"source_version={args.source_version}")
    print(
        f"verification_batch_id="
        f"{args.verification_batch_id}"
    )
    print(f"commission_account={args.commission_account}")
    print(
        f"fee_per_contract_side="
        f"{args.fee_per_contract_side}"
    )
    print(f"commission_first_date={first_date}")
    print(f"commission_last_date={last_date}")
    print(
        f"commission_day_count="
        f"{coverage['commission_day_count']}"
    )
    print(
        f"outside_period_fill_count="
        f"{outside['outside_period_fill_count']}"
    )
    print(
        f"outside_period_first_date="
        f"{outside['outside_first_date']}"
    )
    print(
        f"outside_period_last_date="
        f"{outside['outside_last_date']}"
    )
    print(
        f"reconciled_day_count="
        f"{len(verification_rows)}"
    )
    print(f"matched_day_count={matched_count}")
    print(
        f"mismatched_day_count="
        f"{len(verification_rows) - matched_count}"
    )
    print(f"promoted_fill_count={promoted_count}")
    print(f"unresolved_count={len(unresolved)}")

    for row in verification_rows:
        print(
            "DAY_VERIFICATION "
            f"date={row['trade_date']} "
            f"fill_account={row['fill_broker_account']} "
            f"commission_account="
            f"{row['commission_broker_account']} "
            f"fills={row['fill_row_count']} "
            f"contract_sides={row['contract_sides']} "
            f"calculated="
            f"{row['calculated_commission']} "
            f"reported={row['reported_commission']} "
            f"delta={row['reconciliation_delta']} "
            f"status={row['reconciliation_status']}"
        )

    for item in unresolved:
        print(f"UNRESOLVED={item}")

    print(
        f"db_writes_performed="
        f"{1 if args.apply and not unresolved else 0}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("oos_allowed=0")
    print("shadow_allowed=0")
    print("paper_allowed=0")
    print("micro_live_allowed=0")

    if unresolved:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_BLOCKED"
        )
        return 2

    if args.apply:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_READY"
        )
    else:
        print(
            "VERDICT="
            "FINAM_FUTURES_FILL_EVIDENCE_VERIFICATION_V1_DRY_RUN_OK"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
