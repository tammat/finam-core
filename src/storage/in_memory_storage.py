# storage/in_memory_storage.py

class InMemoryStorage(BaseStorage):

    def __init__(self):
        self._fills = []

    def append_fill(self, fill):
        self._fills.append(fill)

    def load_fills(self, symbol=None):
        if symbol:
            return [f for f in self._fills if f.symbol == symbol]
        return list(self._fills)