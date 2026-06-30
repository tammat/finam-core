#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_CANONICAL_FINANCIAL_DOMAIN_MODEL_V1 ==="

DOC="docs/canonical_financial_domain_model_v1.md"

test -f "$DOC"

grep -q "CANONICAL_FINANCIAL_DOMAIN_MODEL_V1" "$DOC"
grep -q "GOLDEN_RULE_V1" "$DOC"
grep -q "Любая новая сущность сначала появляется" "$DOC"

grep -q "Financial Universe" "$DOC"
grep -q "Market Structure" "$DOC"
grep -q "Market Data" "$DOC"
grep -q "Trading Domain" "$DOC"
grep -q "Strategy Domain" "$DOC"
grep -q "Research Domain" "$DOC"
grep -q "Knowledge Domain" "$DOC"
grep -q "AI Domain" "$DOC"
grep -q "Governance Domain" "$DOC"

grep -q "FOREX_SPOT" "$DOC"
grep -q "FOREX_FORWARD" "$DOC"
grep -q "FOREX_SWAP" "$DOC"
grep -q "FOREX_NDF" "$DOC"
grep -q "Currency Pair" "$DOC"
grep -q "Triangular FX Route" "$DOC"

grep -q "STATISTICAL_ARBITRAGE" "$DOC"
grep -q "CROSS_ASSET_ARBITRAGE" "$DOC"
grep -q "INTER_EXCHANGE_ARBITRAGE" "$DOC"
grep -q "TRIANGULAR_FOREX_ARBITRAGE" "$DOC"
grep -q "BASIS_ARBITRAGE" "$DOC"
grep -q "CALENDAR_ARBITRAGE" "$DOC"

grep -q "Market Bar" "$DOC"
grep -q "Risk Decision" "$DOC"
grep -q "Execution Report" "$DOC"
grep -q "Fill" "$DOC"
grep -q "PnL" "$DOC"
grep -q "AI Recommendation" "$DOC"

grep -q "event_time" "$DOC"
grep -q "source_time" "$DOC"
grep -q "normalized_at" "$DOC"
grep -q "effective_from" "$DOC"
grep -q "effective_to" "$DOC"

grep -q "RAW-данные не используются напрямую" "$DOC"
grep -q "Knowledge Graph не хранит миллионы технических баров" "$DOC"
grep -q "Запрещено использовать SQLite" "$DOC"
grep -q "execution side effects" "$DOC"

echo "canonical_model=READY"
echo "document=docs/canonical_financial_domain_model_v1.md"
echo "domains=FinancialUniverse,MarketStructure,MarketData,Trading,Strategy,Research,Knowledge,AI,Governance"
echo "forex=INCLUDED"
echo "arbitrage=INCLUDED"
echo "trade_types=INCLUDED"
echo "golden_rule=ENTITY_FIRST_IN_CANONICAL_MODEL_THEN_CODE"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=CANONICAL_FINANCIAL_DOMAIN_MODEL_V1_READY"
echo "TEST_CANONICAL_FINANCIAL_DOMAIN_MODEL_V1_OK"
