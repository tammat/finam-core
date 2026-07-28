from pathlib import Path


def test_algorithm_summary_uses_one_ranked_fingerprint() -> None:
    resolver = Path(
        "src/marketcore/presentation/workspace_v2/resolver/research_v2_resolver.py"
    ).read_text()
    assert "row_number() OVER" in resolver
    assert "r.best_rank=1" in resolver
    assert "r.folds_passed best_folds" in resolver
    assert "r.net_profit_factor" in resolver
    assert "max(folds_passed) best_folds" not in resolver
