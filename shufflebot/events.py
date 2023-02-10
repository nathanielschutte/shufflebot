
import asyncio, traceback

class Events:
    def __init__(self) -> None:
        self.events = {}
        self.loop = asyncio.get_event_loop()

    def emit(self, event, *args, **kwargs):
        if event not in self.events:
            return

        for callback in list(self.events[event]):
            try:
                if asyncio.iscoroutinefunction(callback):
                    self.loop.create_task(callback(*args, **kwargs))
                else:
                    if callable(callback):
                        callback(*args, **kwargs)
            except:
                traceback.print_exc()
    
    def on(self, event, callback):
        if event not in self.events:
            self.events[event] = []
        self.events[event].append(callback)
        return self
    
    def off(self, event, callback):
        if event not in self.events:
            return
        self.events[event].remove(callback)

        if not self.events[event]:
            del self.events

        return self

    def once(self, event, callback):
        def _callback(*args, **kwargs):
            self.off(event, _callback)
            return callback(*args, **kwargs)

        return self.on(event, _callback)
