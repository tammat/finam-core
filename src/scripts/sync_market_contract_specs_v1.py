from __future__ import annotations
import argparse

import json
import os
import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import psycopg2
import psycopg2.extras
import requests


DB = os.getenv("DATABASE_URL", "postgresql:///finam_core")
SOURCE_VERSION = "MOEX_ISS_CONTRACT_SPEC_V1"
TIMEOUT_SECONDS = float(os.getenv("CONTRACT_SPEC_HTTP_TIMEOUT_SECONDS", "15"))


class SpecNotApplicable(ValueError):
    """The symbol may remain in research history but has no executable MOEX spec."""


@dataclass(frozen=True)
class Spec:
    symbol: str
    exchange_code: str
    asset_class: str
    currency_code: str
    instrument_name: str
    lot_size: Decimal
    quantity_step: Decimal
    underlying_units: Decimal
    tick_size: Decimal
    tick_value: Decimal
    contract_multiplier: Decimal
    price_precision: int
    initial_margin: Decimal | None
    buy_sell_fee: Decimal | None
    scalper_fee: Decimal | None
    source_payload: dict[str, Any]


def _rows(block: dict[str, Any]) -> list[dict[str, Any]]:
    columns = block.get("columns") or []
    return [dict(zip(columns, row)) for row in (block.get("data") or [])]


def _positive(value: Any, field: str) -> Decimal:
    result = Decimal(str(value or "0"))
    if result <= 0:
        raise ValueError(f"INVALID_{field}")
    return result


def _get(url: str) -> dict[str, Any]:
    response = requests.get(url, timeout=TIMEOUT_SECONDS, headers={"User-Agent": "MarketCore/contract-spec-v1"})
    response.raise_for_status()
    return response.json()


def fetch_spec(symbol: str) -> Spec:
    secid = symbol.split("@", 1)[0]
    if symbol.endswith("@RTSX"):
        url = f"https://iss.moex.com/iss/engines/futures/markets/forts/securities/{secid}.json?iss.meta=off"
        rows = _rows(_get(url).get("securities") or {})
        row = next((item for item in rows if item.get("SECID") == secid), None)
        if not row:
            raise ValueError("MOEX_SECURITY_NOT_FOUND")
        tick_size = _positive(row.get("MINSTEP"), "MINSTEP")
        tick_value = _positive(row.get("STEPPRICE"), "STEPPRICE")
        return Spec(
            symbol, "RTSX", "FUTURES", "RUB", str(row.get("SECNAME") or row.get("SHORTNAME") or secid),
            _positive(row.get("LOTVOLUME"), "LOTVOLUME"), Decimal("1"),
            _positive(row.get("LOTVOLUME"), "LOTVOLUME"), tick_size, tick_value,
            tick_value / tick_size, int(row.get("DECIMALS") or 0),
            _positive(row.get("INITIALMARGIN"), "INITIALMARGIN"),
            _positive(row.get("BUYSELLFEE"), "BUYSELLFEE"),
            _positive(row.get("SCALPERFEE"), "SCALPERFEE"),row,
        )

    if symbol == "CNYRUB_TOM@MISX":
        url = f"https://iss.moex.com/iss/engines/currency/markets/selt/securities/{secid}.json?iss.meta=off"
        rows = _rows(_get(url).get("securities") or {})
        row = next((item for item in rows if item.get("SECID") == secid and item.get("BOARDID") == "CETS"), None)
        asset_class = "CURRENCY"
    elif symbol.endswith("@MISX"):
        url = f"https://iss.moex.com/iss/engines/stock/markets/shares/securities/{secid}.json?iss.meta=off"
        rows = _rows(_get(url).get("securities") or {})
        row = next((item for item in rows if item.get("SECID") == secid and item.get("BOARDID") == "TQBR"), None)
        asset_class = "EQUITY"
    else:
        raise ValueError("INSTRUMENT_NOT_EXECUTABLE")
    if not row:
        if symbol.endswith("-RM@MISX") and not rows:
            raise SpecNotApplicable("MOEX_FOREIGN_SHARE_REFERENCE_UNAVAILABLE")
        raise ValueError("MOEX_EXECUTION_BOARD_NOT_FOUND")
    tick_size = _positive(row.get("MINSTEP"), "MINSTEP")
    return Spec(
        symbol, "MISX", asset_class, "RUB", str(row.get("SECNAME") or row.get("SHORTNAME") or secid),
        _positive(row.get("LOTSIZE"), "LOTSIZE"), _positive(row.get("LOTSIZE"), "LOTSIZE"),
        Decimal("1"), tick_size, tick_size, Decimal("1"),
        int(row.get("DECIMALS") or 0),None,None,None,row,
    )


def same_spec(row: dict[str, Any], spec: Spec) -> bool:
    return all(Decimal(str(row[field])) == value for field, value in (
        ("lot_size", spec.lot_size), ("tick_size", spec.tick_size),
        ("tick_value", spec.tick_value), ("contract_multiplier", spec.contract_multiplier),
    )) and int(row["price_precision"]) == spec.price_precision



def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync MarketCore contract specifications from MOEX ISS."
    )

    parser.add_argument(
        "--symbol",
        action="append",
        default=[],
        help=(
            "Sync only the specified concrete symbol. "
            "May be supplied multiple times."
        ),
    )

    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Expose the requested symbol set without "
            "opening PostgreSQL or performing writes."
        ),
    )

    return parser

def main() -> int:
    args = build_parser().parse_args()

    requested_symbols = tuple(
        dict.fromkeys(
            symbol.strip()
            for symbol in args.symbol
            if symbol.strip()
        )
    )

    # --dry-run является полностью диагностическим режимом:
    # PostgreSQL не открывается и никаких записей не выполняется.
    if args.dry_run:
        if not requested_symbols:
            raise SystemExit(
                "dry_run_requires_at_least_one_symbol"
            )

        print("dry_run=1")
        print(f"symbol_count={len(requested_symbols)}")

        for symbol in requested_symbols:
            print(f"DRY_RUN_SYMBOL symbol={symbol}")

        print("db_writes_performed=0")
        print("runtime_changed=0")
        print("execution_changed=0")
        print("orders_changed=0")
        print("fills_changed=0")
        print("micro_live_allowed=0")
        print(
            "VERDICT="
            "MARKET_CONTRACT_SPEC_SYNC_V1_DRY_RUN_READY"
        )
        return 0

    run_id = uuid.uuid4()
    written = unchanged = skipped = failed = 0

    with psycopg2.connect(DB) as connection:
        with connection.cursor(
            cursor_factory=psycopg2.extras.RealDictCursor
        ) as cursor:
            cursor.execute(
                """INSERT INTO analytics.contract_spec_sync_run_v1(run_id,status_code)
                VALUES(%s,'RUNNING')""",
                (str(run_id),),
            )

            # Explicit --symbol является authoritative selector.
            # Это позволяет синхронизировать исторические concrete
            # contracts, отсутствующие в 7-day active universe.
            if requested_symbols:
                symbols = list(requested_symbols)
            else:
                cursor.execute(
                    """SELECT DISTINCT symbol FROM public.market_bars
                    WHERE timeframe='M5'
                      AND ts>=clock_timestamp()-interval '7 days'
                      AND source NOT IN (
                          'unknown',
                          'synthetic_futures_backfill_v1'
                      )
                      AND (
                          symbol LIKE '%@MISX'
                          OR symbol LIKE '%@RTSX'
                      )
                    ORDER BY symbol"""
                )
                symbols = [
                    row["symbol"]
                    for row in cursor.fetchall()
                ]

            connection.commit()

            for symbol in symbols:
                try:
                    spec = fetch_spec(symbol)
                    cursor.execute("""INSERT INTO analytics.market_instrument_v1
                      (symbol,exchange_code,asset_class,currency_code,instrument_name,
                       is_active,eligibility_scope,source_version)
                      VALUES(%s,%s,%s,%s,%s,true,'RESEARCH',%s)
                      ON CONFLICT(symbol) DO UPDATE SET exchange_code=EXCLUDED.exchange_code,
                        asset_class=EXCLUDED.asset_class,currency_code=EXCLUDED.currency_code,
                        instrument_name=EXCLUDED.instrument_name,is_active=true,
                        source_version=EXCLUDED.source_version,updated_at=clock_timestamp()""",
                      (spec.symbol,spec.exchange_code,spec.asset_class,spec.currency_code,
                       spec.instrument_name,SOURCE_VERSION))
                    cursor.execute("""SELECT * FROM analytics.market_contract_spec_v1
                        WHERE symbol=%s AND is_active ORDER BY valid_from DESC LIMIT 1""", (symbol,))
                    current = cursor.fetchone()
                    if current and current["source_version"] == SOURCE_VERSION and same_spec(current, spec):
                        outcome = "UNCHANGED"
                        unchanged += 1
                    else:
                        cursor.execute("""UPDATE analytics.market_contract_spec_v1
                            SET is_active=false,valid_to=clock_timestamp(),updated_at=clock_timestamp()
                            WHERE symbol=%s AND is_active""", (symbol,))
                        cursor.execute("""INSERT INTO analytics.market_contract_spec_v1
                          (symbol,lot_size,tick_size,tick_value,contract_multiplier,price_precision,
                           is_active,source_version)
                          VALUES(%s,%s,%s,%s,%s,%s,true,%s)""",
                          (symbol,spec.lot_size,spec.tick_size,spec.tick_value,
                           spec.contract_multiplier,spec.price_precision,SOURCE_VERSION))
                        outcome = "UPDATED" if current else "CREATED"
                        written += 1
                    cursor.execute("""INSERT INTO analytics.market_contract_execution_spec_v2
                      (symbol,quantity_step,underlying_units,source_version,updated_at)
                      VALUES(%s,%s,%s,%s,clock_timestamp()) ON CONFLICT(symbol) DO UPDATE SET
                       quantity_step=EXCLUDED.quantity_step,underlying_units=EXCLUDED.underlying_units,
                       source_version=EXCLUDED.source_version,updated_at=EXCLUDED.updated_at""",
                      (symbol,spec.quantity_step,spec.underlying_units,SOURCE_VERSION))
                    if spec.asset_class == "FUTURES":
                        cursor.execute("""INSERT INTO analytics.market_contract_cost_spec_v1
                          (symbol,initial_margin,buy_sell_fee,scalper_fee,negotiated_fee,exercise_fee,source_version,source_payload,verified_at)
                          VALUES(%s,%s,%s,%s,%s,%s,%s,%s::jsonb,clock_timestamp()) ON CONFLICT(symbol) DO UPDATE SET
                            initial_margin=EXCLUDED.initial_margin,buy_sell_fee=EXCLUDED.buy_sell_fee,
                            scalper_fee=EXCLUDED.scalper_fee,negotiated_fee=EXCLUDED.negotiated_fee,
                            exercise_fee=EXCLUDED.exercise_fee,source_version=EXCLUDED.source_version,
                            source_payload=EXCLUDED.source_payload,verified_at=EXCLUDED.verified_at""",
                          (symbol,spec.initial_margin,spec.buy_sell_fee,spec.scalper_fee,
                           spec.source_payload.get("NEGOTIATEDFEE"),spec.source_payload.get("EXERCISEFEE"),
                           SOURCE_VERSION,json.dumps(spec.source_payload,default=str)))
                        cursor.execute("""UPDATE public.margin_requirements SET initial_margin=%s,
                          maintenance_margin=%s,base_symbol=%s,asset_class='FUTURES',currency='RUB',
                          source=%s,active=true,updated_at=clock_timestamp(),raw_json=%s::jsonb WHERE symbol=%s""",
                          (spec.initial_margin,spec.initial_margin,symbol.split('@')[0],SOURCE_VERSION,
                           json.dumps(spec.source_payload,default=str),symbol))
                        if cursor.rowcount == 0:
                            cursor.execute("""INSERT INTO public.margin_requirements
                              (symbol,base_symbol,asset_class,initial_margin,maintenance_margin,currency,source,active,raw_json)
                              VALUES(%s,%s,'FUTURES',%s,%s,'RUB',%s,true,%s::jsonb)""",
                              (symbol,symbol.split('@')[0],spec.initial_margin,spec.initial_margin,SOURCE_VERSION,
                               json.dumps(spec.source_payload,default=str)))
                    cursor.execute("""INSERT INTO analytics.contract_spec_sync_item_v1
                      (run_id,symbol,status_code,reason_code,source_version,source_payload)
                      VALUES(%s,%s,%s,'MOEX_ISS_VALIDATED',%s,%s::jsonb)""",
                      (str(run_id),symbol,outcome,SOURCE_VERSION,json.dumps(spec.source_payload,default=str)))
                    connection.commit()
                except SpecNotApplicable as exc:
                    connection.rollback()
                    skipped += 1
                    cursor.execute("""INSERT INTO analytics.contract_spec_sync_item_v1
                      (run_id,symbol,status_code,reason_code,source_version,source_payload)
                      VALUES(%s,%s,'SKIPPED',%s,%s,'{}'::jsonb)""",
                      (str(run_id),symbol,str(exc)[:300],SOURCE_VERSION))
                    connection.commit()
                except Exception as exc:
                    connection.rollback()
                    if str(exc) == "MOEX_SECURITY_NOT_FOUND":
                        cursor.execute("""SELECT EXISTS(SELECT 1 FROM runtime_active_universe
                          WHERE symbol=%s AND is_enabled) active""", (symbol,))
                        active = bool(cursor.fetchone()["active"])
                        if not active:
                            skipped += 1
                            cursor.execute("""INSERT INTO analytics.contract_spec_sync_item_v1
                              (run_id,symbol,status_code,reason_code,source_version,source_payload)
                              VALUES(%s,%s,'SKIPPED','EXPIRED_OR_INACTIVE_CONTRACT',%s,'{}'::jsonb)""",
                              (str(run_id),symbol,SOURCE_VERSION))
                            connection.commit()
                            continue
                    failed += 1
                    cursor.execute("""INSERT INTO analytics.contract_spec_sync_item_v1
                      (run_id,symbol,status_code,reason_code,source_version,source_payload)
                      VALUES(%s,%s,'FAILED',%s,%s,'{}'::jsonb)""",
                      (str(run_id),symbol,str(exc)[:300],SOURCE_VERSION))
                    connection.commit()

            status = "SUCCEEDED" if failed == 0 else "PARTIAL"
            cursor.execute("""UPDATE analytics.contract_spec_sync_run_v1 SET status_code=%s,
                symbols_total=%s,symbols_written=%s,symbols_unchanged=%s,symbols_failed=%s,
                finished_at=clock_timestamp(),updated_at=clock_timestamp() WHERE run_id=%s""",
                (status,len(symbols),written,unchanged+skipped,failed,str(run_id)))
    print(f"spec_sync_run_id={run_id}")
    print(f"symbols={len(symbols)}")
    print(f"specs_written={written}")
    print(f"specs_unchanged={unchanged}")
    print(f"specs_skipped={skipped}")
    print(f"specs_failed={failed}")
    print("runtime_changed=0")
    print("live_allowed=0")
    print("VERDICT=CONTRACT_SPEC_SYNC_V1_OK")
    return 0 if failed == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
