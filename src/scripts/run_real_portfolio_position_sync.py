from __future__ import annotations

import os
import grpc
import psycopg2

from finam_core.auth.token_manager import FinamTokenManager
from finam_proto.grpc.tradeapi.v1.accounts import (
    accounts_service_pb2,
    accounts_service_pb2_grpc,
)


def _decimal_value(obj) -> float:
    try:
        return float(getattr(obj, "value", obj) or 0.0)
    except Exception:
        return 0.0


def main() -> int:
    dsn = os.getenv("DATABASE_URL")
    if not dsn:
        raise RuntimeError("DATABASE_URL is empty")

    account_id = os.getenv("FINAM_ACCOUNT_ID", "").strip()
    if not account_id:
        raise RuntimeError("FINAM_ACCOUNT_ID is empty")

    symbol_filter = os.getenv("REAL_POSITION_SYNC_SYMBOL", "").strip().upper()
    endpoint = os.getenv("FINAM_GRPC_ENDPOINT", "api.finam.ru:443").strip()
    timeout = float(os.getenv("BROKER_POSITION_SYNC_TIMEOUT_SEC", "10"))

    jwt = FinamTokenManager().get_token()

    channel = grpc.secure_channel(endpoint, grpc.ssl_channel_credentials())
    stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

    try:
        resp = stub.GetAccount(
            accounts_service_pb2.GetAccountRequest(account_id=account_id),
            metadata=(("authorization", f"Bearer {jwt}"),),
            timeout=timeout,
        )
    except Exception as exc:
        print(
            f"REAL_PORTFOLIO_POSITION_SYNC_SOURCE_UNAVAILABLE "
            f"error={type(exc).__name__}:{exc}",
            flush=True,
        )
        return 0

    conn = psycopg2.connect(dsn)
    updated = 0
    scanned = 0

    with conn:
        with conn.cursor() as cur:
            cur.execute("""
                create table if not exists real_portfolio_positions (
                    symbol text primary key,
                    qty numeric not null default 0,
                    avg_price numeric,
                    current_price numeric,
                    market_value numeric,
                    pnl numeric,
                    source text,
                    updated_at timestamptz not null default now()
                )
            """)

            for pos in getattr(resp, "positions", []) or []:
                symbol = str(getattr(pos, "symbol", "") or "").upper()
                if not symbol:
                    continue

                if symbol_filter and symbol != symbol_filter:
                    continue

                scanned += 1

                qty = _decimal_value(getattr(pos, "quantity", None))
                avg_price = _decimal_value(getattr(pos, "average_price", None))

                cur.execute("""
                    insert into real_portfolio_positions (
                        symbol,
                        qty,
                        avg_price,
                        current_price,
                        market_value,
                        pnl,
                        source,
                        updated_at
                    )
                    values (
                        %s,
                        %s,
                        %s,
                        0,
                        0,
                        0,
                        'finam_account_getaccount',
                        now()
                    )
                    on conflict (symbol) do update
                    set
                        qty = excluded.qty,
                        avg_price = excluded.avg_price,
                        source = excluded.source,
                        updated_at = now()
                """, (
                    symbol,
                    qty,
                    avg_price,
                ))

                updated += 1

                print(
                    f"REAL_PORTFOLIO_POSITION_SYNC_UPDATE "
                    f"symbol={symbol} qty={qty} avg_price={avg_price}",
                    flush=True,
                )

    print(
        f"REAL_PORTFOLIO_POSITION_SYNC_OK scanned={scanned} updated={updated}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
