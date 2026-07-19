from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_materializer_excludes_quarantined_fills() -> None:
    text = (ROOT / "src/scripts/analytics/materialize_closed_trades_from_fills_v1.py").read_text()
    assert "paper_fill_anomaly_quarantine_v1" in text
    assert "f.ts>=q.range_start AND f.ts<q.range_end" in text


def test_detector_finds_one_sided_unlinked_storms() -> None:
    text = (ROOT / "src/scripts/detect_paper_fill_anomalies_v1.py").read_text()
    assert "ONE_SIDED_UNLINKED_FILL_STORM" in text
    assert "linked_count = 0" in text
    assert "opposite.side<>h.side" in text


def test_known_ngk6_incident_is_seeded_and_job_is_scheduled() -> None:
    text = (ROOT / "sql/analytics/137_paper_fill_anomaly_quarantine_v1.sql").read_text()
    assert "NGK6_20260506_ONE_SIDED_STORM" in text
    assert "11861" in text
    assert "PAPER_FILL_ANOMALY_DETECTOR_V1" in text
