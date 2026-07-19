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


def _record_sync_state(dsn: str, status: str, *, scanned: int = 0, changed: int = 0,
                       zeroed: int = 0, error: str | None = None) -> None:
    with psycopg2.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO analytics.broker_position_sync_state_v1(
                       worker_code,status_code,last_attempt_at,last_success_at,last_failure_at,
                       positions_scanned,positions_changed,positions_zeroed,last_error,updated_at)
                   VALUES('FINAM_POSITION_SYNC',%s,clock_timestamp(),
                     CASE WHEN %s='HEALTHY' THEN clock_timestamp() END,
                     CASE WHEN %s='FAILED' THEN clock_timestamp() END,%s,%s,%s,%s,clock_timestamp())
                   ON CONFLICT(worker_code) DO UPDATE SET
                     status_code=excluded.status_code,last_attempt_at=excluded.last_attempt_at,
                     last_success_at=coalesce(excluded.last_success_at,analytics.broker_position_sync_state_v1.last_success_at),
                     last_failure_at=coalesce(excluded.last_failure_at,analytics.broker_position_sync_state_v1.last_failure_at),
                     positions_scanned=excluded.positions_scanned,
                     positions_changed=excluded.positions_changed,
                     positions_zeroed=excluded.positions_zeroed,last_error=excluded.last_error,
                     updated_at=clock_timestamp()""",
                (status, status, status, scanned, changed, zeroed, error),
            )


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
        detail = f"{type(exc).__name__}:{exc}"[:2000]
        try:
            _record_sync_state(dsn, "FAILED", error=detail)
        except Exception:
            pass
        print(
            f"REAL_PORTFOLIO_POSITION_SYNC_SOURCE_UNAVAILABLE "
            f"error={detail}",
            flush=True,
        )
        return 2

    conn = psycopg2.connect(dsn)
    changed = 0
    zeroed = 0
    scanned = 0
    seen_symbols: set[str] = set()

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
                seen_symbols.add(symbol)

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
                    WHERE real_portfolio_positions.qty IS DISTINCT FROM excluded.qty
                       OR real_portfolio_positions.avg_price IS DISTINCT FROM excluded.avg_price
                    RETURNING symbol
                """, (
                    symbol,
                    qty,
                    avg_price,
                ))

                changed += int(cur.fetchone() is not None)

            if symbol_filter:
                cur.execute(
                    """UPDATE real_portfolio_positions SET qty=0,updated_at=now()
                       WHERE symbol=%s AND qty<>0 AND NOT(symbol=ANY(%s))""",
                    (symbol_filter, list(seen_symbols)),
                )
            else:
                cur.execute(
                    """UPDATE real_portfolio_positions SET qty=0,updated_at=now()
                       WHERE source='finam_account_getaccount' AND qty<>0
                         AND NOT(symbol=ANY(%s))""",
                    (list(seen_symbols),),
                )
            zeroed = cur.rowcount

    _record_sync_state(dsn, "HEALTHY", scanned=scanned, changed=changed, zeroed=zeroed)

    print(
        f"REAL_PORTFOLIO_POSITION_SYNC_OK scanned={scanned} changed={changed} zeroed={zeroed}",
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
