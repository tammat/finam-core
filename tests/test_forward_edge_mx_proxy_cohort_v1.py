import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "build_forward_edge_mx_proxy_cohort_v1.py"
SPEC = importlib.util.spec_from_file_location("mx_proxy_cohort", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_only_imoex_is_replaced_with_execution_proxy() -> None:
    assert MODULE.proxy_symbol("IMOEX") == "MXU6@RTSX"
    assert MODULE.proxy_symbol("IMOEX2") == "IMOEX2"
    assert MODULE.proxy_symbol("BR_ROLLING@RTSX") == "BR_ROLLING@RTSX"
