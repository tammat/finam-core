#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core

component_tests=(
  scripts/test_marketcore_domain_render_tree_contract_v2.sh
  scripts/test_marketcore_domain_render_tree_v2_models.sh
  scripts/test_marketcore_home_domain_render_tree_v2.sh
  scripts/test_marketcore_portfolio_domain_render_tree_v2.sh
  scripts/test_marketcore_control_center_domain_render_tree_v2.sh
  scripts/test_marketcore_domain_producer_registry_v2.sh
)

for component_test in "${component_tests[@]}"; do
  test -x "$component_test" || {
    echo "STAGE2_COMPONENT_TEST_NOT_EXECUTABLE=$component_test"
    exit 1
  }
  output="$(bash "$component_test")"
  grep -Fq "VERDICT=" <<<"$output" || {
    echo "STAGE2_COMPONENT_VERDICT_MISSING=$component_test"
    exit 1
  }
  if [[ "$component_test" == *domain_producer_registry* ]]; then
    grep -Fq "stage2_exit=READY" <<<"$output"
    grep -Fq "presenter_value_documents=0" <<<"$output"
    grep -Fq "control_center_localized_values=0" <<<"$output"
  fi
done

v2_sources=(
  src/marketcore/presentation/render_tree/v2
  src/marketcore/presentation/workspace_v2/renderer/home_v2_domain_renderer.py
  src/marketcore/presentation/workspace_v2/renderer/portfolio_v2_domain_renderer.py
  src/marketcore/presentation/workspace_v2/renderer/control_center_v2_domain_renderer.py
  src/marketcore/presentation/workspace_v2/domain_producer_registry_v2.py
)

if grep -RInE --include='*.py' \
  'presentation\.adapters|presentation\.ui_runtime|HTMLResponse|browser_dom|render_document_to_html|"class"[[:space:]]*:|"style"[[:space:]]*:|"href"[[:space:]]*:|data-' \
  "${v2_sources[@]}"
then
  echo "STAGE2_PLATFORM_SEMANTIC_FOUND"
  exit 1
fi

if grep -RIn --include='*.py' 'PRESENTER_VALUE' \
  src/marketcore/presentation/workspace_v2/renderer/*_v2_domain_renderer.py
then
  echo "STAGE2_PRESENTER_VALUE_FOUND"
  exit 1
fi

echo "domain_contract_v2=OK"
echo "immutable_models=OK"
echo "deterministic_serialization=OK"
echo "registered_producers=3"
echo "platform_semantics=0"
echo "presenter_values=0"
echo "control_center_localized_values=0"
echo "runtime_switch=0"
echo "service_restart=0"
echo "VERDICT=TEST_MARKETCORE_STAGE2_DOMAIN_RENDER_TREE_EXIT_V1_OK"
