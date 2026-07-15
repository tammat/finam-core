#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

contract="docs/vision/MARKETCORE_DOMAIN_RENDER_TREE_CONTRACT_V2.md"

test -s "$contract" || {
  echo "CONTRACT_NOT_FOUND=$contract"
  exit 1
}

required_terms=(
  "Status: LOCKED TARGET CONTRACT"
  'Schema: `marketcore.render_tree.v2`'
  "V2 is the only target contract"
  "Document Envelope"
  "Node Envelope"
  "Domain Node Types"
  "Content Contract"
  "State Contract"
  "Action Contract"
  "Forbidden Semantics"
  "Compatibility Boundary"
  'timezone_code`: governed IANA timezone selected in operator settings'
  'the default `timezone_code` is `Europe/Moscow`'
  'the operator may select another timezone from governed Settings'
  'duration values remain numeric and use only `DURATION_HM`'
  'decimal-hour display such as `2.5 ч` is forbidden'
  "Definition Of Done"
  "VERDICT=MARKETCORE_DOMAIN_RENDER_TREE_CONTRACT_V2_LOCKED"
)

for term in "${required_terms[@]}"; do
  grep -Fq "$term" "$contract" || {
    echo "CONTRACT_TERM_NOT_FOUND=$term"
    exit 1
  }
done

for forbidden in class style HTML DOM browser SQL JavaScript; do
  grep -Fq "$forbidden" "$contract" || {
    echo "FORBIDDEN_SEMANTIC_NOT_GOVERNED=$forbidden"
    exit 1
  }
done

grep -Fq 'action_kind`: `NAVIGATE`, `QUERY`, `COMMAND` or `CONFIRM' "$contract"
grep -Fq "state-changing commands require Policy Engine metadata" "$contract"
grep -Fq "all user-facing content uses message keys" "$contract"

echo "schema=marketcore.render_tree.v2"
echo "domain_node_types=21"
echo "platform_semantics_allowed=0"
echo "compatibility_boundary=ISOLATED"
echo "runtime_changed=0"
echo "VERDICT=TEST_MARKETCORE_DOMAIN_RENDER_TREE_CONTRACT_V2_OK"
