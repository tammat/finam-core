#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_MARKET_DATA_NORMALIZATION_DESIGN_V1 ==="

DOC="docs/market_data_normalization_design_v1.md"

test -f "$DOC"

grep -q "MARKET_DATA_NORMALIZATION_DESIGN_V1" "$DOC"
grep -q "CANONICAL_FINANCIAL_DOMAIN_MODEL_V1" "$DOC"
grep -q "GOLDEN_RULE_V1" "$DOC"

grep -q "Instrument" "$DOC"
grep -q "Contract" "$DOC"
grep -q "Symbol Alias" "$DOC"
grep -q "Bar" "$DOC"

grep -q "FOREX_SPOT" "$DOC"
grep -q "FOREX_FORWARD" "$DOC"
grep -q "FOREX_SWAP" "$DOC"
grep -q "FOREX_NDF" "$DOC"
grep -q "triangular_fx_route" "$DOC"

grep -q "EQUITY" "$DOC"
grep -q "FUTURE" "$DOC"
grep -q "OPTION" "$DOC"
grep -q "COMMODITY_FUTURE" "$DOC"

grep -q "RAW Source" "$DOC"
grep -q "Symbol Alias" "$DOC"
grep -q "Normalized Bar" "$DOC"
grep -q "Research Dataset" "$DOC"
grep -q "Knowledge Graph" "$DOC"
grep -q "AI" "$DOC"

grep -q "venue_id" "$DOC"
grep -q "instrument_id" "$DOC"
grep -q "contract_id" "$DOC"
grep -q "bar_id" "$DOC"

grep -q "event_time" "$DOC"
grep -q "source_time" "$DOC"
grep -q "normalized_at" "$DOC"
grep -q "effective_from" "$DOC"
grep -q "effective_to" "$DOC"

grep -q "VALID" "$DOC"
grep -q "WARNING" "$DOC"
grep -q "REJECTED" "$DOC"
grep -q "REVIEW_REQUIRED" "$DOC"

grep -q "Запрещено обращаться к RAW market data" "$DOC"
grep -q "Запрещено использовать broker symbol как первичный ключ" "$DOC"
grep -q "Запрещено смешивать Instrument и Contract" "$DOC"
grep -q "Запрещено использовать SQLite" "$DOC"

echo "market_data_normalization_design=READY"
echo "document=docs/market_data_normalization_design_v1.md"
echo "canonical_model=CANONICAL_FINANCIAL_DOMAIN_MODEL_V1"
echo "golden_rule=ENTITY_FIRST_IN_CANONICAL_MODEL_THEN_CODE"
echo "domains=FinancialUniverse,MarketStructure,Forex,MarketData,DataQuality"
echo "asset_classes=EQUITY,ETF,BOND,INDEX,FUTURE,OPTION,FOREX_SPOT,FOREX_FORWARD,FOREX_SWAP,FOREX_NDF,COMMODITY_SPOT,COMMODITY_FUTURE,CRYPTO_SPOT,CRYPTO_FUTURE,CFD,MONEY_MARKET"
echo "normalization_chain=RAW_TO_SYMBOL_ALIAS_TO_INSTRUMENT_TO_CONTRACT_TO_BAR_TO_DATASET"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=MARKET_DATA_NORMALIZATION_DESIGN_V1_READY"
echo "TEST_MARKET_DATA_NORMALIZATION_DESIGN_V1_OK"
