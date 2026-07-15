from scripts.build_session_execution_edge_v1 import microstructure_quality


class Cursor:
    def __init__(self, value):
        self.value = value

    def execute(self, *_args):
        return None

    def fetchone(self):
        return self.value


def test_microstructure_quality_matches_execution_result_constraint() -> None:
    assert microstructure_quality(Cursor(None), "IMOEX") == "BAR_ONLY"
    assert microstructure_quality(Cursor({"market_data_quality": "COLLECTING"}), "IMOEX") == "BAR_ONLY"
    assert microstructure_quality(Cursor({"market_data_quality": "QUOTE_VERIFIED"}), "SBER@MISX") == "QUOTE_VERIFIED"
