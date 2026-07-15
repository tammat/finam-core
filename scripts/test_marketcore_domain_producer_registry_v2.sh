#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

registry="src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py"

test -f "$registry"

PYTHONPYCACHEPREFIX=/tmp/marketcore_domain_producer_registry_v2 \
PYTHONPATH=src \
python3 -m py_compile "$registry"

if grep -nE 'presentation\.adapters|presentation\.ui_runtime|HTMLResponse|browser_dom|"href"|http://|https://|/workspace-v2|response_class' "$registry"
then
  echo "DOMAIN_PRODUCER_REGISTRY_PLATFORM_DEPENDENCY_FOUND"
  exit 1
fi

PYTHONPATH=src .venv/bin/python - <<'PY'
import re

from marketcore.presentation.render_tree.v2 import render_document_v2_to_dict, render_document_v2_to_json
from marketcore.presentation.workspace_v2.domain_producer_registry_v2 import (
    DomainProducerCodeV2,
    DomainProducerRegistryErrorV2,
    build_domain_document_v2,
    domain_producer_definitions_v2,
)


definitions = domain_producer_definitions_v2()
assert tuple(item.producer_code for item in definitions) == tuple(DomainProducerCodeV2)
assert len({item.document_id for item in definitions}) == 3

documents = {
    code: build_domain_document_v2(code, timezone_code="Europe/Moscow")
    for code in DomainProducerCodeV2
}

expected_ids = {
    DomainProducerCodeV2.HOME: "operator.home.v2",
    DomainProducerCodeV2.PORTFOLIO: "operator.portfolio.v2",
    DomainProducerCodeV2.CONTROL_CENTER: "operator.control_center.v2",
}

for code, document in documents.items():
    assert document.document_id == expected_ids[code]
    assert document.schema_version == "marketcore.render_tree.v2"
    assert document.timezone_code == "Europe/Moscow"
    payload = render_document_v2_to_json(document)
    assert '"class"' not in payload
    assert '"style"' not in payload
    assert '"href"' not in payload
    assert "/workspace-v2" not in payload

utc_home = build_domain_document_v2("home", timezone_code="UTC")
assert utc_home.timezone_code == "UTC"

try:
    build_domain_document_v2("UNKNOWN")
except DomainProducerRegistryErrorV2 as exc:
    assert str(exc) == "DOMAIN_PRODUCER_V2_UNKNOWN:UNKNOWN"
else:
    raise AssertionError("UNKNOWN_PRODUCER_NOT_REJECTED")

presenter_value_documents = sum(
    '"format_code":"PRESENTER_VALUE"' in render_document_v2_to_json(document)
    for document in documents.values()
)
assert presenter_value_documents == 0

print("registered_producers=3")
print("valid_v2_documents=3")
print("platform_semantics=0")
print("settings_timezone=OK")
print(f"presenter_value_documents={presenter_value_documents}")
print("stage2_presenter_value_gate=OK")

control_payload = render_document_v2_to_dict(documents[DomainProducerCodeV2.CONTROL_CENTER])
localized_values = []
def collect_localized_values(node):
    value = node.get("content", {}).get("value")
    if isinstance(value, str) and re.search(r"[А-Яа-яЁё]", value):
        localized_values.append(value)
    for child in node.get("children", []):
        collect_localized_values(child)

collect_localized_values(control_payload["root"])
assert localized_values
print(f"control_center_localized_values={len(localized_values)}")
print("stage2_exit=BLOCKED_BY_LOCALIZED_DOMAIN_VALUES")
PY

echo "runtime_switch=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_DOMAIN_PRODUCER_REGISTRY_V2_OK"
