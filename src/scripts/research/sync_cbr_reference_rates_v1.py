from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
from decimal import Decimal
import xml.etree.ElementTree as ET

import psycopg2
import requests

from finam_core.analytics.statistics_repository import build_psycopg_url


CBR_URL = "https://www.cbr.ru/scripts/XML_dynamic.asp"
USD_CBR_CODE = "R01235"
SOURCE_VERSION = "CBR_OFFICIAL_XML_DYNAMIC_V1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--from-date",
        required=True,
        type=date.fromisoformat,
    )

    parser.add_argument(
        "--to-date",
        required=True,
        type=date.fromisoformat,
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
    )

    return parser.parse_args()


def fetch_rates(
    from_date: date,
    to_date: date,
) -> list[tuple[date, Decimal]]:
    response = requests.get(
        CBR_URL,
        params={
            "date_req1": from_date.strftime("%d/%m/%Y"),
            "date_req2": to_date.strftime("%d/%m/%Y"),
            "VAL_NM_RQ": USD_CBR_CODE,
        },
        timeout=30,
        headers={
            "User-Agent":
                "MarketCore/CBR-reference-rate-sync-v1"
        },
    )

    response.raise_for_status()

    root = ET.fromstring(response.content)

    rows: list[tuple[date, Decimal]] = []

    for record in root.findall("Record"):
        raw_date = record.attrib["Date"]

        day, month, year = map(
            int,
            raw_date.split("."),
        )

        value_text = record.findtext("Value")

        if value_text is None:
            raise ValueError(
                "CBR_RATE_VALUE_MISSING"
            )

        value = Decimal(
            value_text.replace(",", ".")
        )

        if value <= 0:
            raise ValueError(
                "CBR_RATE_NOT_POSITIVE"
            )

        rows.append(
            (
                date(year, month, day),
                value,
            )
        )

    return rows


def main() -> int:
    args = parse_args()

    if args.to_date < args.from_date:
        raise SystemExit(
            "ERROR=INVALID_DATE_RANGE"
        )

    rates = fetch_rates(
        args.from_date,
        args.to_date,
    )

    print(f"rate_count={len(rates)}")
    print(f"from_date={args.from_date}")
    print(f"to_date={args.to_date}")

    for rate_date, rate_value in rates:
        print(
            "CBR_RATE "
            f"currency=USD "
            f"cbr_code={USD_CBR_CODE} "
            f"rate_date={rate_date} "
            f"rate_value={rate_value}"
        )

    if args.dry_run:
        print("db_writes_performed=0")
        print(
            "VERDICT="
            "CBR_REFERENCE_RATE_SYNC_V1_DRY_RUN_READY"
        )
        return 0

    with psycopg2.connect(
        build_psycopg_url()
    ) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                CREATE TABLE IF NOT EXISTS
                    analytics.cbr_reference_rate_v1
                (
                    currency_code text NOT NULL,
                    cbr_code text NOT NULL,
                    rate_date date NOT NULL,
                    rate_value numeric NOT NULL,
                    source_version text NOT NULL,
                    source_retrieved_at timestamptz NOT NULL,
                    PRIMARY KEY (
                        currency_code,
                        rate_date
                    ),
                    CHECK (rate_value > 0)
                )
                """
            )

            retrieved_at = datetime.now(
                timezone.utc
            )

            for rate_date, rate_value in rates:
                cur.execute(
                    """
                    INSERT INTO
                        analytics.cbr_reference_rate_v1
                    (
                        currency_code,
                        cbr_code,
                        rate_date,
                        rate_value,
                        source_version,
                        source_retrieved_at
                    )
                    VALUES (
                        'USD',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    ON CONFLICT (
                        currency_code,
                        rate_date
                    )
                    DO UPDATE SET
                        cbr_code =
                            EXCLUDED.cbr_code,
                        rate_value =
                            EXCLUDED.rate_value,
                        source_version =
                            EXCLUDED.source_version,
                        source_retrieved_at =
                            EXCLUDED.source_retrieved_at
                    """,
                    (
                        USD_CBR_CODE,
                        rate_date,
                        rate_value,
                        SOURCE_VERSION,
                        retrieved_at,
                    ),
                )

        conn.commit()

    print(
        f"db_rows_written={len(rates)}"
    )
    print("runtime_changed=0")
    print("execution_changed=0")
    print("orders_changed=0")
    print("fills_changed=0")
    print("micro_live_allowed=0")
    print(
        "VERDICT="
        "CBR_REFERENCE_RATE_SYNC_V1_READY"
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
