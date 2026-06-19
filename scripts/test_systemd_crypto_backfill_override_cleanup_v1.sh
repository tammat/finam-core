#!/usr/bin/env bash
set -euo pipefail

OVERRIDE="/etc/systemd/system/finam-crypto-backfill.service.d/override.conf"

echo "=== TEST SYSTEMD CRYPTO BACKFILL OVERRIDE CLEANUP V1 ==="
echo "runtime_allow=0"
echo "execution_enabled=0"
echo "real_trading_enabled=0"
echo "telegram_service_untouched=1"

test -f "$OVERRIDE"

first_nonempty="$(grep -m1 -v '^[[:space:]]*$' "$OVERRIDE" || true)"

if [[ "$first_nonempty" != \[* ]]; then
  echo "CRYPTO_BACKFILL_OVERRIDE_BAD first_nonempty=$first_nonempty"
  exit 1
fi

systemd-analyze verify finam-crypto-backfill.service >/tmp/crypto_backfill_verify.log 2>&1 || {
  cat /tmp/crypto_backfill_verify.log
  exit 1
}

if grep -q "Assignment outside of section" /tmp/crypto_backfill_verify.log; then
  cat /tmp/crypto_backfill_verify.log
  exit 1
fi

systemd-analyze verify /etc/systemd/system/finam-multi-asset-breakout-telegram.service >/tmp/multi_asset_telegram_verify.log 2>&1 || {
  cat /tmp/multi_asset_telegram_verify.log
  exit 1
}

echo "CRYPTO_BACKFILL_OVERRIDE_FIRST_LINE_OK first_nonempty=$first_nonempty"
echo "CRYPTO_BACKFILL_SYSTEMD_VERIFY_OK"
echo "MULTI_ASSET_TELEGRAM_SYSTEMD_VERIFY_OK"
echo "VERDICT=SYSTEMD_CRYPTO_BACKFILL_OVERRIDE_CLEANUP_OK"
echo "TEST_SYSTEMD_CRYPTO_BACKFILL_OVERRIDE_CLEANUP_V1_OK"
