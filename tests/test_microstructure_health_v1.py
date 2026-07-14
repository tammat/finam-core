from datetime import datetime
import importlib.util
from pathlib import Path
from zoneinfo import ZoneInfo


SCRIPT = Path(__file__).resolve().parents[1] / "src" / "scripts" / "build_microstructure_health_v1.py"
SPEC = importlib.util.spec_from_file_location("microstructure_health", SCRIPT)
assert SPEC is not None and SPEC.loader is not None
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)
POLICY = {"session_timezone": "Europe/Moscow", "session_start": "06:50", "session_end": "23:50"}


def test_session_window_is_weekday_and_timezone_aware() -> None:
    tz = ZoneInfo("Europe/Moscow")
    assert MODULE.session_is_open(datetime(2026, 7, 14, 10, 0, tzinfo=tz), POLICY) is True
    assert MODULE.session_is_open(datetime(2026, 7, 12, 10, 0, tzinfo=tz), POLICY) is False
