#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import urllib.request
from datetime import date, datetime, timedelta

import psycopg2

DATABASE_URL = os.environ["DATABASE_URL"]

ROOTS = [x.strip().upper() for x in os.getenv("CONTRACT_CALENDAR_ROOTS", "BR,NG").split(",") if x.strip()]
HORIZON_DAYS = int(os.getenv("CONTRACT_CALENDAR_HORIZON_DAYS", "370"))

DDL = """
CREATE TABLE IF NOT EXISTS futures_contract_calendar (
    symbol text PRIMARY KEY,
    root_symbol text NOT NULL,
    contract_role text NOT NULL DEFAULT 'UNKNOWN',
    last_trade_date date NOT NULL,
    expiration_date date,
    source text NOT NULL DEFAULT 'manual',
    updated_at timestamptz NOT NULL DEFAULT now()
);
"""

UPSERT = """
INSERT INTO futures_contract_calendar
(symbol, root_symbol, contract_role, last_trade_date, expiration_date, source, updated_at)
VALUES (%s,%s,%s,%s,%s,%s,now())
ON CONFLICT (symbol) DO UPDATE SET
    root_symbol=EXCLUDED.root_symbol,
    contract_role=EXCLUDED.contract_role,
    last_trade_date=EXCLUDED.last_trade_date,
    expiration_date=EXCLUDED.expiration_date,
    source=EXCLUDED.source,
    updated_at=now();
"""

def fetch_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def parse_date(value):
    if not value:
        return None
    return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()

def fetch_all_forts_securities() -> list[dict]:
    # Русский комментарий: один bounded-запрос вместо потенциально бесконечной пагинации.
    url = (
        "https://iss.moex.com/iss/engines/futures/markets/forts/"
        "securities.json?iss.meta=off&limit=1000"
    )
    data = fetch_json(url)

    sec = data.get("securities") or {}
    columns = sec.get("columns") or []
    rows = sec.get("data") or []

    return [dict(zip(columns, row)) for row in rows]

def match_root(secid: str) -> str | None:
    secid_u = secid.upper()
    for root in ROOTS:
        if secid_u.startswith(root):
            return root
    return None

def role_for(index: int) -> str:
    if index == 0:
        return "CURRENT"
    if index == 1:
        return "NEXT"
    return "FUTURE"

def main() -> None:
    today = date.today()
    horizon_to = today + timedelta(days=HORIZON_DAYS)

    print("=== CONTRACT CALENDAR SEED V2 ===")
    print("mode=research_only")
    print("execution=disabled")
    print("runtime_changed=0")
    print(f"roots={','.join(ROOTS)}")
    print(f"horizon_days={HORIZON_DAYS}")
    print(f"date_from={today.isoformat()}")
    print(f"date_to={horizon_to.isoformat()}")
    print()

    all_rows = fetch_all_forts_securities()

    grouped: dict[str, list[dict]] = {root: [] for root in ROOTS}

    for row in all_rows:
        secid = str(row.get("SECID") or "").upper()
        root = match_root(secid)
        if not root:
            continue

        last_trade = parse_date(row.get("LASTTRADEDATE"))
        expiration = parse_date(row.get("LASTDELDATE"))

        if not last_trade:
            continue

        if last_trade < today or last_trade > horizon_to:
            continue

        grouped[root].append({
            "secid": secid,
            "symbol": f"{secid}@RTSX",
            "root": root,
            "last_trade_date": last_trade,
            "expiration_date": expiration,
        })

    total_written = 0

    with psycopg2.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            cur.execute(DDL)

            for root in ROOTS:
                contracts = sorted(grouped.get(root, []), key=lambda x: x["last_trade_date"])

                for idx, item in enumerate(contracts):
                    role = role_for(idx)

                    cur.execute(
                        UPSERT,
                        (
                            item["symbol"],
                            item["root"],
                            role,
                            item["last_trade_date"],
                            item["expiration_date"],
                            "moex_iss_chain_v2",
                        ),
                    )
                    total_written += 1

                    print(
                        "SEED_ROW "
                        f"root={item['root']} "
                        f"symbol={item['symbol']} "
                        f"role={role} "
                        f"last_trade_date={item['last_trade_date']} "
                        f"expiration_date={item['expiration_date']} "
                        f"source=moex_iss_chain_v2"
                    )

            conn.commit()

    print()
    print(f"TOTAL_WRITTEN={total_written}")
    print("VERDICT=CONTRACT_CALENDAR_CHAIN_SEEDED")
    print("CONTRACT_CALENDAR_SEED_V2_OK")

if __name__ == "__main__":
    main()
