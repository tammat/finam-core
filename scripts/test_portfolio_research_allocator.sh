#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/research/portfolio_research_allocator.py \
  src/scripts/allocate_research_portfolio.py

python src/scripts/allocate_research_portfolio.py --help >/dev/null

python - <<'PY'
from finam_core.research.portfolio_research_allocator import (
    PortfolioResearchAllocator,
    ResearchInstrumentCandidate,
)

items = [
    ResearchInstrumentCandidate("LKOH@MISX", 10, 100.0, 10.0, 0.5, 15.0),
    ResearchInstrumentCandidate("PLZL@MISX", 8, 80.0, 8.0, 0.6, 12.0),
    ResearchInstrumentCandidate("SBER@MISX", 10, -5.0, -0.5, 0.4, 1.0),
]

result = PortfolioResearchAllocator().allocate(items, max_symbol_weight=0.5)

assert len(result) == 3
assert result[0].decision == "РАСПРЕДЕЛИТЬ"
assert result[1].decision == "РАСПРЕДЕЛИТЬ"
assert result[2].decision == "НЕ_РАСПРЕДЕЛЯТЬ"

print("OK: portfolio research allocator")
PY
