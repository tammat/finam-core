#!/usr/bin/env bash
set -euo pipefail

cd /opt/finam-core || exit 1

echo "=== TEST_ARCHITECTURE_FREEZE_V1 ==="

test -f ARCHITECTURE_FREEZE_V1.md

grep -q "FINAM CORE — ARCHITECTURE FREEZE V1" ARCHITECTURE_FREEZE_V1.md
grep -q "Статус: APPROVED" ARCHITECTURE_FREEZE_V1.md
grep -q "Research Platform" ARCHITECTURE_FREEZE_V1.md
grep -q "Candidate Registry" ARCHITECTURE_FREEZE_V1.md
grep -q "Research Knowledge Base" ARCHITECTURE_FREEZE_V1.md
grep -q "RESEARCH_UNIVERSE_V1" ARCHITECTURE_FREEZE_V1.md
grep -q "DISCOVER STATISTICAL EDGE" ARCHITECTURE_FREEZE_V1.md
grep -q "Минимальная архитектурная достаточность" ARCHITECTURE_FREEZE_V1.md

echo "TEST_ARCHITECTURE_FREEZE_V1_OK"
