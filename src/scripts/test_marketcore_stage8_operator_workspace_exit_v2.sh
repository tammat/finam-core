#!/usr/bin/env bash
set -euo pipefail
cd /opt/finam-core

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 120 venv/bin/pytest -q \
  tests/test_operator_decision_workspace_v2.py \
  tests/test_operator_decision_selection_v2.py \
  tests/test_home_operator_decision_render_tree_v2.py \
  tests/test_operator_decision_workspace_cycle_v2.py \
  tests/test_operator_decision_lineage_audit_v2.py

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 60 venv/bin/python \
  src/scripts/build_operator_decision_workspace_v2.py

test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2")" -eq 5
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 WHERE quality_code<>'UNVERIFIED' OR policy_verdict NOT IN ('REVIEW_REQUIRED','BLOCKED') OR autonomy_mode NOT IN ('OPERATOR_APPROVAL','OBSERVE_ONLY')")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 WHERE source_as_of IS NULL OR source_identity<>'analytics.profit_funnel_transition_lineage_v2' OR evidence='{}'::jsonb OR expires_at<=clock_timestamp()")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 d JOIN analytics.profit_funnel_transition_lineage_v2 l USING(transition_code) WHERE (d.evidence->>'from_count')::bigint<>l.from_count OR (d.evidence->>'to_count')::bigint<>l.to_count OR (d.evidence->>'linked_count')::bigint<>l.linked_count OR d.loss_source_code<>l.reason_code")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(DISTINCT transition_code) FROM analytics.operator_decision_lineage_audit_v2")" -eq 5
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 d WHERE NOT EXISTS (SELECT 1 FROM analytics.operator_decision_lineage_audit_v2 a WHERE a.decision_id=d.decision_id AND a.lineage_hash=md5(concat_ws('|',d.transition_code,d.action_code,d.source_identity,d.source_as_of::text,d.evidence::text,d.policy_verdict,d.autonomy_mode,d.selection_status,d.feedback_status,coalesce(d.actual_result::text,''))))")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM public.orders WHERE exchange_order_id IS NOT NULL")" -eq 0
test "$(psql -d finam_core -Atqc "SELECT count(*) FROM analytics.operator_decision_workspace_v2 WHERE quality_code='UNVERIFIED' AND policy_verdict NOT IN ('REVIEW_REQUIRED','BLOCKED')")" -eq 0

systemctl is-enabled --quiet marketcore-operator-decision-workspace.timer
systemctl is-active --quiet marketcore-operator-decision-workspace.timer

PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src timeout 30 venv/bin/python - <<'PY'
import json
import urllib.request

home = json.load(urllib.request.urlopen("http://127.0.0.1:8080/api/v2/domain-render-tree/home", timeout=10))
catalog = json.load(urllib.request.urlopen("http://127.0.0.1:8080/api/v2/i18n/catalog?locale=ru-RU", timeout=10))["messages"]
domain_keys = []
raw_codes = []
cards = []

def walk(node):
    node_id = node.get("node_id", "")
    content = node.get("content") or {}
    if node_id.startswith("home.operator.action.") and node.get("type") == "card":
        cards.append(node)
    if node_id.startswith("home.operator."):
        key = content.get("message_key", "")
        if key.startswith("home.operator.domain."):
            domain_keys.append(key)
        if content.get("format_code") == "DOMAIN_CODE":
            raw_codes.append(node_id)
    for child in node.get("children", []):
        walk(child)

walk(home["root"])
assert len(cards) == 5
assert domain_keys and not raw_codes
assert not (set(domain_keys) - set(catalog))
print(f"render_tree_actions={len(cards)}")
print(f"localized_domain_values={len(domain_keys)}")
PY

echo "ranked_actions=5"
echo "decision_lineage_reproducible=PASS"
echo "decision_lineage_audited=PASS"
echo "green_unverified_actions=0"
echo "real_trading_changed=0"
echo "operator_workspace_timer=ACTIVE"
echo "VERDICT=MARKETCORE_STAGE8_OPERATOR_WORKSPACE_EXIT_GATE_PASS"
