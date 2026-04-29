# src/scripts/show_account_pretty.py

import os

import grpc
from google.protobuf.json_format import MessageToDict

from finam_core.auth.token_manager import FinamTokenManager

from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2
from finam_proto.grpc.tradeapi.v1.accounts import accounts_service_pb2_grpc


def _fail_network_hint(exc: Exception) -> None:
    msg = str(exc)
    print("ERROR: Finam API connection/auth failed")
    print(f"DETAIL: {msg}")
    if "198.18." in msg or "No route to host" in msg or "Socket closed" in msg:
        print("HINT: похоже, api.finam.ru уходит в VPN/proxy fake-IP 198.18.x.x. Отключите VPN или добавьте api.finam.ru в DIRECT/bypass.")
    raise SystemExit(2)


def _to_float_decimal(d):
    if not d:
        return 0.0
    return float(d.get("value", 0.0))


def _money_to_float(m):
    if not m:
        return 0.0
    units = float(m.get("units", 0))
    nanos = float(m.get("nanos", 0)) / 1e9
    return units + nanos


def print_header(data):
    equity = _to_float_decimal(data.get("equity"))
    unreal = _to_float_decimal(data.get("unrealized_profit"))

    mc = data.get("portfolio_mc", {})
    available_cash = _to_float_decimal(mc.get("available_cash"))
    init_margin = _to_float_decimal(mc.get("initial_margin"))
    maint_margin = _to_float_decimal(mc.get("maintenance_margin"))

    print("=" * 60)
    print(f"ACCOUNT: {data.get('account_id')}")
    print(f"STATUS : {data.get('status')}")
    print("-" * 60)
    print(f"Equity           : {equity:,.2f}")
    print(f"Unrealized PnL   : {unreal:,.2f}")
    print(f"Available cash   : {available_cash:,.2f}")
    print(f"Initial margin   : {init_margin:,.2f}")
    print(f"Maintenance marg.: {maint_margin:,.2f}")
    print("=" * 60)


def print_cash(data):
    print("\nCASH:")
    for c in data.get("cash", []):
        val = _money_to_float(c)
        print(f"  {c.get('currency_code')}: {val:,.2f}")


def print_positions(data):
    print("\nPOSITIONS:")

    positions = data.get("positions", [])

    if not positions:
        print("  NO POSITIONS")
        return

    total_exposure = 0.0
    total_pnl = 0.0

    for p in positions:
        symbol = p.get("symbol")

        qty = _to_float_decimal(p.get("quantity"))
        avg = _to_float_decimal(p.get("average_price"))
        cur = _to_float_decimal(p.get("current_price"))
        pnl = _to_float_decimal(p.get("unrealized_pnl"))

        side = "LONG" if qty > 0 else "SHORT"
        exposure = abs(qty * cur)

        total_exposure += exposure
        total_pnl += pnl

        print(
            f"{symbol:20} {side:5} "
            f"qty={qty:8.2f} "
            f"avg={avg:10.2f} "
            f"px={cur:10.2f} "
            f"PnL={pnl:10.2f}"
        )

    print("-" * 60)
    print(f"TOTAL EXPOSURE: {total_exposure:,.2f}")
    print(f"TOTAL UNREAL  : {total_pnl:,.2f}")


def print_risk_flags(data):
    print("\nRISK FLAGS:")

    for p in data.get("positions", []):
        symbol = p.get("symbol")
        pnl = _to_float_decimal(p.get("unrealized_pnl"))

        if pnl < -1000:
            print(f"  ⚠ LARGE LOSS: {symbol} {pnl:,.2f}")

        qty = _to_float_decimal(p.get("quantity"))
        if qty < 0:
            print(f"  ⚠ SHORT POSITION: {symbol} qty={qty}")


def main():
    account_id = os.getenv("FINAM_ACCOUNT_ID") or os.getenv("ACCOUNT_ID")
    if not account_id:
        raise RuntimeError("FINAM_ACCOUNT_ID/ACCOUNT_ID is required")

    host = os.getenv("FINAM_HOST") or os.getenv("FINAM_GRPC_HOST") or "api.finam.ru:443"

    tm = FinamTokenManager()
    try:
        jwt = os.getenv("FINAM_JWT", "") or tm.get_token()
    except Exception as exc:
        _fail_network_hint(exc)

    channel = grpc.secure_channel(host, grpc.ssl_channel_credentials())
    stub = accounts_service_pb2_grpc.AccountsServiceStub(channel)

    req = accounts_service_pb2.GetAccountRequest(account_id=account_id)
    try:
        resp = stub.GetAccount(req, metadata=[("authorization", f"Bearer {jwt}")], timeout=20)
    except Exception as exc:
        _fail_network_hint(exc)

    data = MessageToDict(resp, preserving_proto_field_name=True)

    print_header(data)
    print_cash(data)
    print_positions(data)
    print_risk_flags(data)


if __name__ == "__main__":
    main()