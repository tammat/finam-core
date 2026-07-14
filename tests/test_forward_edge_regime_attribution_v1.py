from pathlib import Path


def test_regime_attribution_is_causal_and_freshness_bounded() -> None:
    script = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "scripts"
        / "build_forward_edge_regime_attribution_v1.py"
    ).read_text(encoding="utf-8")

    assert "s.ts<=o.entry_ts" in script
    assert "s.ts>=o.entry_ts-(%s::interval)" in script
    assert "MAX_SNAPSHOT_AGE = \"15 minutes\"" in script
    assert "COALESCE(r.regime, 'UNKNOWN')" in script
