#!/usr/bin/env bash
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

echo "=== TEST FUTURES REAL BLOCK GUARD BROKER WIRING V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"

python3 -m py_compile \
  src/finam_core/risk/futures_real_block_guard_v1.py \
  src/finam_core/execution/finam_order_client_adapter.py

PYTHONPATH=src python3 - <<'PY'
from finam_core.execution.finam_order_client_adapter import FinamOrderClientAdapter


class FakeClient:
    def __init__(self):
        self.calls = []

    def place_limit_order(self, **kwargs):
        self.calls.append(("limit", kwargs))
        return {"status": "ACCEPTED", "order_id": "LIMIT-1"}

    def place_market_order(self, **kwargs):
        self.calls.append(("market", kwargs))
        return {"status": "ACCEPTED", "order_id": "MARKET-1"}


def assert_blocked(result, client, name):
    print(
        "CASE "
        f"name={name} "
        f"ok={int(result.ok)} "
        f"broker_order_id={result.broker_order_id} "
        f"reason={result.reason} "
        f"client_calls={len(client.calls)}"
    )

    if result.ok:
        raise SystemExit(f"FAIL: {name} should be blocked")

    if result.reason != "FUTURES_REAL_TRADING_BLOCKED_UNTIL_2026_07_01":
        raise SystemExit(f"FAIL: {name} unexpected reason={result.reason}")

    if client.calls:
        raise SystemExit(f"FAIL: {name} called broker client")


def assert_allowed(result, client, name):
    print(
        "CASE "
        f"name={name} "
        f"ok={int(result.ok)} "
        f"broker_order_id={result.broker_order_id} "
        f"reason={result.reason} "
        f"client_calls={len(client.calls)}"
    )

    if not result.ok:
        raise SystemExit(f"FAIL: {name} should be allowed")

    if not client.calls:
        raise SystemExit(f"FAIL: {name} did not call broker client")


# Futures must be blocked before client call.
client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_blocked(
    adapter.place_buy_limit(symbol="BRN6@RTSX", qty=1, price=80.0),
    client,
    "block_br_buy_limit",
)

client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_blocked(
    adapter.place_sell_limit(symbol="NGQ6@RTSX", qty=1, price=3.2),
    client,
    "block_ng_sell_limit",
)

client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_blocked(
    adapter.place_buy_market(symbol="GDU6@RTSX", qty=1),
    client,
    "block_gold_buy_market",
)

client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_blocked(
    adapter.place_sell_market(symbol="USDRUBF@RTSX", qty=1),
    client,
    "block_usdrubf_sell_market",
)

# Equity must pass through guard and reach fake broker.
client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_allowed(
    adapter.place_buy_limit(symbol="SBER@MISX", qty=1, price=300.0),
    client,
    "allow_sber_buy_limit",
)

client = FakeClient()
adapter = FinamOrderClientAdapter(client)
assert_allowed(
    adapter.place_sell_market(symbol="SBER@MISX", qty=1),
    client,
    "allow_sber_sell_market",
)

print("FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1_OK")
PY

grep -q "FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1" src/finam_core/execution/finam_order_client_adapter.py
grep -q "evaluate_futures_real_block_v1" src/finam_core/execution/finam_order_client_adapter.py

echo TEST_FUTURES_REAL_BLOCK_GUARD_BROKER_WIRING_V1_OK
