from accounting.position_manager import PositionManager
from storage.fill_journal import FillJournal


def replay():
    pm = PositionManager()
    journal = FillJournal()

    records = journal.read_all()

    for r in records:
        fill_data = r["fill"]

        class DummyFill:
            pass

        fill = DummyFill()
        for k, v in fill_data.items():
            setattr(fill, k, v)

        pm.apply_fill(fill)

    print("Replayed equity:", pm.total_equity())


if __name__ == "__main__":
    replay()