from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / "src/scripts/run_db_job_scheduler_v1.py"


def load_scheduler():
    spec = spec_from_file_location("resource_guard_scheduler", PATH)
    module = module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def test_heavy_research_is_deferred_when_four_core_host_is_busy(monkeypatch) -> None:
    scheduler = load_scheduler()
    monkeypatch.setattr(scheduler, "load_average_1m", lambda: 3.2)
    monkeypatch.setenv("RESEARCH_HEAVY_LOAD_LIMIT", "3.0")
    allowed, load_1m, limit, reason = scheduler.resource_gate("CHECKPOINTED_WALKFORWARD_V4")
    assert allowed is False
    assert (load_1m, limit, reason) == (3.2, 3.0, "HOST_LOAD_ABOVE_LIMIT")


def test_light_online_job_is_never_deferred_by_research_load(monkeypatch) -> None:
    scheduler = load_scheduler()
    monkeypatch.setattr(scheduler, "load_average_1m", lambda: 9.0)
    allowed, _, _, reason = scheduler.resource_gate("MONDAY_READINESS_V1")
    assert allowed is True
    assert reason == "ONLINE_OR_LIGHT_JOB"


def test_scheduler_keeps_one_heavy_job_and_audits_every_gate() -> None:
    source = PATH.read_text(encoding="utf-8")
    assert "LOCK_ID = 941903128" in source
    assert "HEAVY_EXECUTORS" in source
    assert "research_resource_gate_audit_v1" in source
    assert "DB_JOB_DEFERRED" in source


def test_home_reports_resource_deferrals_without_running_research() -> None:
    resolver = (ROOT / "src/marketcore/presentation/workspace_v2/resolver/"
                "control_compact_v3_resolver.py").read_text(encoding="utf-8")
    renderer = (ROOT / "src/marketcore/presentation/workspace_v2/renderer/"
                "home_compact_v1_domain_renderer.py").read_text(encoding="utf-8")
    assert "research_resource_gate_audit_v1" in resolver
    assert "Ресурсы исследований" in renderer
