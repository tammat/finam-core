#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

test -f sql/20260511_trade_source_contract.sql

grep -q "ADD COLUMN IF NOT EXISTS trade_source" sql/20260511_trade_source_contract.sql
grep -q "SET trade_source = 'manual'" sql/20260511_trade_source_contract.sql
grep -q "idx_trades_trade_source" sql/20260511_trade_source_contract.sql
grep -q "idx_trades_symbol_trade_source" sql/20260511_trade_source_contract.sql

! grep -q "raw_json" sql/20260511_trade_source_contract.sql
! grep -q "execution_type" sql/20260511_trade_source_contract.sql

echo "TRADE_SOURCE_CONTRACT_TEST_OK"
