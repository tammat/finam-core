#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=src

python3 -m py_compile \
  src/finam_core/governance/guard_candidate_classification_reader.py \
  src/finam_core/pipelines/paper_pipeline.py

grep -q "GuardCandidateClassificationReader" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_GUARD_CLASSIFICATION_STATE_LOADED" src/finam_core/pipelines/paper_pipeline.py
grep -q "PIPE_GUARD_CLASSIFICATION_ADVISORY" src/finam_core/pipelines/paper_pipeline.py
grep -q "advisory_only=1" src/finam_core/pipelines/paper_pipeline.py
grep -q "_guard_classification_advisory_v1" src/finam_core/pipelines/paper_pipeline.py

echo CLASSIFICATION_ADVISORY_PIPELINE_V1_OK
