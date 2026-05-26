#!/usr/bin/env python3
import argparse
import os

import psycopg


REQUIRED_SECTIONS = ("market", "strategy", "execution", "risk", "raw_payload")


def split_csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]


def section_status(snapshot: dict, section: str) -> tuple[bool, int, int]:
    data = snapshot.get(section)
    if not isinstance(data, dict):
        return False, 0, 0

    total = len(data)
    filled = sum(1 for v in data.values() if v not in (None, "", {}, []))
    return filled > 0, filled, total


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--limit", type=int, default=100)
    parser.add_argument("--event-type", default="paper_trade")
    args = parser.parse_args()

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise SystemExit("DATABASE_URL is not set")

    symbols = split_csv(args.symbols)

    sql = """
    select
        trade_id,
        symbol,
        strategy,
        timeframe,
        event_type,
        created_at,
        snapshot
    from trade_context_snapshots
    where symbol = any(%(symbols)s)
      and event_type = %(event_type)s
    order by created_at desc
    limit %(limit)s;
    """

    rows = []
    with psycopg.connect(database_url) as conn:
        with conn.cursor(row_factory=psycopg.rows.dict_row) as cur:
            cur.execute(
                sql,
                {
                    "symbols": symbols,
                    "event_type": args.event_type,
                    "limit": args.limit,
                },
            )
            rows = list(cur.fetchall())

    print(
        "SNAPSHOT_COMPLETENESS_REPORT",
        f"symbols={','.join(symbols)}",
        f"event_type={args.event_type}",
        f"rows={len(rows)}",
        flush=True,
    )

    if not rows:
        print("SNAPSHOT_COMPLETENESS status=NO_DATA")
        return

    section_ok = {name: 0 for name in REQUIRED_SECTIONS}
    section_total = {name: 0 for name in REQUIRED_SECTIONS}
    section_filled = {name: 0 for name in REQUIRED_SECTIONS}

    weak = 0

    for row in rows:
        snapshot = row["snapshot"] or {}
        missing = []

        for section in REQUIRED_SECTIONS:
            ok, filled, total = section_status(snapshot, section)
            if ok:
                section_ok[section] += 1
            else:
                missing.append(section)

            section_filled[section] += filled
            section_total[section] += total

        status = "OK" if not missing else "PARTIAL"
        if missing:
            weak += 1

        print(
            "SNAPSHOT_ROW",
            f"status={status}",
            f"trade_id={row['trade_id']}",
            f"symbol={row['symbol']}",
            f"strategy={row['strategy']}",
            f"timeframe={row['timeframe']}",
            f"missing={','.join(missing) if missing else '-'}",
            flush=True,
        )

    total_rows = len(rows)
    ok_rows = total_rows - weak
    completeness = ok_rows / total_rows if total_rows else 0.0

    print(
        "SNAPSHOT_COMPLETENESS_SUMMARY",
        f"rows={total_rows}",
        f"ok_rows={ok_rows}",
        f"partial_rows={weak}",
        f"row_completeness={completeness:.4f}",
        flush=True,
    )

    for section in REQUIRED_SECTIONS:
        coverage = section_ok[section] / total_rows if total_rows else 0.0
        field_fill = (
            section_filled[section] / section_total[section]
            if section_total[section]
            else 0.0
        )

        print(
            "SNAPSHOT_SECTION",
            f"section={section}",
            f"rows_with_data={section_ok[section]}",
            f"coverage={coverage:.4f}",
            f"field_fill={field_fill:.4f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
