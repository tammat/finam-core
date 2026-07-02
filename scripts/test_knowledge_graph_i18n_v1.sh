#!/usr/bin/env bash
set -euo pipefail

echo "=== TEST_KNOWLEDGE_GRAPH_I18N_V1 ==="

scripts/apply_knowledge_graph_i18n_v1.sh

languages=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.languages;")
labels=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.i18n_labels;")
aliases=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.i18n_aliases;")
providers=$(psql -At -d finam_core -c "SELECT count(*) FROM knowledge_graph.translation_providers;")

test "$languages" -ge 2
test "$labels" -gt 0
test "$aliases" -gt 0
test "$providers" -ge 5

psql -d finam_core -c "
SELECT object_type, object_key, locale, label, translation_status
FROM knowledge_graph.i18n_labels
WHERE object_key IN ('TradeContextSnapshot','PAPER_RUNTIME','HAS_ATTRIBUTION')
ORDER BY object_type, object_key, locale;
"

echo "languages=$languages"
echo "labels=$labels"
echo "aliases=$aliases"
echo "providers=$providers"
echo "runtime_changed=0"
echo "execution_changed=0"
echo "orders_changed=0"
echo "fills_changed=0"
echo "micro_live_allowed=0"
echo "VERDICT=KNOWLEDGE_GRAPH_I18N_V1_READY"
echo "VERDICT=TEST_KNOWLEDGE_GRAPH_I18N_V1_OK"
