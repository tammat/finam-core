import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "expand_forward_edge_imoex2_v1.py"
SPEC = importlib.util.spec_from_file_location("imoex2_expansion", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_candidate_identity_is_stable_and_target_specific() -> None:
    row = {
        "incubator_candidate_id": "073df27b-2bbb-5b06-94a7-605c57652219",
        "timeframe": "M5",
        "frozen_parameter_json": {"lookback": 96, "holding_bars": 6},
    }
    candidate_id, fingerprint = MODULE.candidate_identity(row)
    assert str(candidate_id) == str(MODULE.candidate_identity(row)[0])
    assert len(fingerprint) == 64
    assert MODULE.TARGET_SYMBOL == "IMOEX2"
