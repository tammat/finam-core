from __future__ import annotations

import importlib.util
from pathlib import Path
import uuid

import psycopg2.extensions


SCRIPT_PATH = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "scripts"
    / "project_forward_edge_shadow_trailing_v1.py"
)
SPEC = importlib.util.spec_from_file_location("project_forward_edge_shadow_trailing_v1", SCRIPT_PATH)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_build_variant_id_is_deterministic_and_postgres_adaptable() -> None:
    observation_id = uuid.UUID("d95ad748-a017-4a61-bb59-07318cc17062")

    first = MODULE.build_variant_id(observation_id)
    second = MODULE.build_variant_id(str(observation_id))

    assert first == second
    assert str(uuid.UUID(first)) == first
    assert psycopg2.extensions.adapt(first).getquoted() == f"'{first}'".encode()
