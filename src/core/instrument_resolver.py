from data.contract_mapper import resolve

class InstrumentResolver:
    def resolve(self, symbol: str) -> str:
        return resolve(symbol)