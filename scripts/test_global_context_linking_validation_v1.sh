#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_GLOBAL_CONTEXT_LINKING_VALIDATION_V1 ==="

python3 -m py_compile \
src/scripts/research/build_global_context_linking_validation_v1.py

src/scripts/research/build_global_context_linking_validation_v1.py \
| tee /tmp/global_context_linking_validation_v1.out

grep -q "GLOBAL_CONTEXT_LINKING_VALIDATION_V1" \
/tmp/global_context_linking_validation_v1.out

grep -q "linked_trades=480" \
/tmp/global_context_linking_validation_v1.out

grep -q "context=ENERGY_BR links=480" \
/tmp/global_context_linking_validation_v1.out

grep -q "context=FX_USDRUB links=480" \
/tmp/global_context_linking_validation_v1.out

grep -q "context_links_total=960" \
/tmp/global_context_linking_validation_v1.out

grep -q "duplicates=0" \
/tmp/global_context_linking_validation_v1.out

grep -q "bad_links=0" \
/tmp/global_context_linking_validation_v1.out

grep -q "expected_links=960" \
/tmp/global_context_linking_validation_v1.out

grep -q "VERDICT=GLOBAL_CONTEXT_LINKING_INCOMPLETE\|VERDICT=GLOBAL_CONTEXT_LINKING_VALIDATION_OK" \
/tmp/global_context_linking_validation_v1.out

echo "TEST_GLOBAL_CONTEXT_LINKING_VALIDATION_V1_OK"
