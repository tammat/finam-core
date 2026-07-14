import importlib.util
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "src" / "scripts" / "ops" / "build_root_contract_rotation_v1.py"
SPEC = importlib.util.spec_from_file_location("root_contract_rotation", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_replace_symbols_rotates_brent_without_changing_other_symbols() -> None:
    command = (
        "/usr/bin/python run_market_pipeline.py --symbol BRN6@RTSX "
        "--symbols BRN6@RTSX,NGN6@RTSX,SBER@MISX --strategy vwap_bands_mr"
    )

    rotated = MODULE.replace_symbols(command, "BRQ6@RTSX", "NGN6@RTSX")

    assert "--symbol BRQ6@RTSX" in rotated
    assert "--symbols BRQ6@RTSX,NGN6@RTSX,SBER@MISX" in rotated
    assert "BRN6@RTSX" not in rotated


def test_deployment_dropin_has_no_expired_brent_contract() -> None:
    dropin = (
        ROOT
        / "deploy"
        / "systemd"
        / "finam-paper-pipeline.service.d"
        / "zzzz-brq6-paper-contract.conf"
    ).read_text()

    assert "BRQ6@RTSX" in dropin
    assert "BRN6@RTSX" not in dropin
