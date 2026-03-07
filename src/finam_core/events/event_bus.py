class EventBus:

    def __init__(self):
        self.subscribers = {}

    def subscribe(self, event_type, handler):

        if event_type not in self.subscribers:
            self.subscribers[event_type] = []

        self.subscribers[event_type].append(handler)
        print(f"BUS subscribe: type={event_type} handler={handler} total={len(self.subscribers[event_type])}",
              flush=True)

    def publish(self, event):
        et = event.get("type", None)
        handlers = self.subscribers.get(et, [])
        print(f"BUS publish: type={et} handlers={len(handlers)} event={event}", flush=True)

        for i, h in enumerate(handlers):
            print(f"BUS call handler[{i}]={h}", flush=True)
            try:
                h(event)
                print(f"BUS handler[{i}] ok", flush=True)
            except Exception as e:
                print(f"BUS handler[{i}] ERROR: {type(e).__name__}: {e}", flush=True)
                raise