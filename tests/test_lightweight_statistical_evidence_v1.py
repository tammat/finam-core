from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
PATH=ROOT/"src/scripts/analytics/build_lightweight_statistical_evidence_v1.py"


def module():
    spec=spec_from_file_location("lightweight_statistics",PATH); result=module_from_spec(spec)
    assert spec and spec.loader; spec.loader.exec_module(result); return result


def test_block_bootstrap_preserves_blocks_and_is_deterministic():
    stats=module(); values=[-1,-.5,.2,.4,1,1.2]*5
    first=stats.moving_block_bootstrap(values,samples=300,seed=7)
    second=stats.moving_block_bootstrap(values,samples=300,seed=7)
    assert first==second
    assert first["block_length"]>1
    assert first["ci_low"]<=first["ci_high"]


def test_mde_is_adaptive_and_negative_edge_never_ready():
    stats=module()
    strong=stats.minimum_detectable_sample([.8,1.0,1.2,.9,1.1]*5)
    weak=stats.minimum_detectable_sample([-1,1.2,-.8,1.1,.2]*5)
    assert strong is not None and strong<=weak
    assert stats.minimum_detectable_sample([-1,-.5,.2]) is None


def test_concentration_and_cusum_are_fail_closed():
    stats=module()
    concentrated=stats.concentration([10,-1,-1,-1],[1,2,3,4])
    assert concentrated["pass"] is False
    drift=stats.cusum_degradation([1.0]*20+[-1.0]*10)
    assert drift["status"]=="DEGRADATION_ALERT"


def test_scheduler_runs_statistics_only_as_resource_gated_heavy_job():
    scheduler=(ROOT/"src/scripts/run_db_job_scheduler_v1.py").read_text()
    migration=(ROOT/"sql/analytics/254_lightweight_statistical_evidence_v1.sql").read_text()
    assert '"LIGHTWEIGHT_STATISTICAL_EVIDENCE_V1"' in scheduler
    assert "HEAVY_EXECUTORS" in scheduler
    assert "V1_RESOURCE_GATED" in migration
    assert "21:20" in migration
