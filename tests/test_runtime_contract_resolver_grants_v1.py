from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_runtime_contract_resolver_has_read_only_grants() -> None:
    text = (ROOT / "sql/analytics/138_runtime_contract_resolver_grants_v1.sql").read_text()
    assert "GRANT SELECT ON analytics.futures_roll_decision_v1 TO finam" in text
    assert "GRANT SELECT ON public.futures_contract_calendar TO finam" in text
    assert "GRANT INSERT" not in text
    assert "GRANT UPDATE" not in text
