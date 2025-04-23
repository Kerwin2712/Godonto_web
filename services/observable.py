class Observable:
    def __init__(self):
        self._observers = []

    def subscribe(self, observer):
        self._observers.append(observer)

    def notify_all(self, event_type, data=None):
        for observer in self._observers:
            observer.on_event(event_type, data)