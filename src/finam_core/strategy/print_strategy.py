class PrintStrategy:

    def __init__(self, execution_engine):

        self.execution = execution_engine
        self.last_price = None

    def on_quote(self, event):

        price = event["last"]

        if price is None:
            return

        if self.last_price and price > self.last_price:

            signal = {
                "symbol": event["symbol"],
                "side": "BUY",
                "qty": 1
            }

            try:
                self.execution.execute_signal(signal)
            except Exception as e:
                print("ORDER ERROR:", e)
        self.last_price = price