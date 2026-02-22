from core.pipeline.full_pipeline import run_full_pipeline

def test_full_pipeline():
    result = run_full_pipeline()
    assert result == "OK"