#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python -m py_compile \
  src/finam_core/strategy/quote_signal_processor.py \
  src/finam_core/strategy/strategy_runtime.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "class QuoteSignalProcessor" src/finam_core/strategy/quote_signal_processor.py
grep -q "QuoteSignalInput" src/finam_core/pipelines/paper_pipeline.py
grep -q "self.quote_signal_processor = QuoteSignalProcessor" src/finam_core/pipelines/paper_pipeline.py
grep -q "quote_signal_processor.process" src/finam_core/pipelines/paper_pipeline.py

echo "OK: quote signal processor compile"
