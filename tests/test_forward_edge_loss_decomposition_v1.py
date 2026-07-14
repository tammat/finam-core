from decimal import Decimal
import importlib.util
from pathlib import Path


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "build_forward_edge_loss_decomposition_v1.py"
SPEC = importlib.util.spec_from_file_location("loss_decomposition", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_reconciliation_identity() -> None:
    row = {
        "reference_gross_pnl": Decimal("20"), "entry_timing_cost": Decimal("3"),
        "commission_cost": Decimal("2"), "spread_cost": Decimal("1"),
        "slippage_cost": Decimal("0.5"), "exit_policy_effect": Decimal("4"),
        "variant_net_pnl": Decimal("17.5"),
    }
    assert MODULE.reconciliation_error(row) == Decimal("0")


def test_dominant_loss_driver_uses_largest_adverse_component() -> None:
    row = {
        "reference_gross_pnl": Decimal("5"), "entry_timing_cost": Decimal("7"),
        "commission_cost": Decimal("2"), "spread_cost": Decimal("0"),
        "slippage_cost": Decimal("0"), "exit_policy_effect": Decimal("-3"),
    }
    assert MODULE.dominant_loss_driver(row) == "ENTRY_TIMING"
