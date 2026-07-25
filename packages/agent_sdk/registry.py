class ConnectorRegistry:
    def __init__(self):
        self._factories = {}

    def register(self, name, factory):
        if not name or not callable(factory):
            raise ValueError("connector name and callable factory required")
        self._factories[name] = factory

    def create(self, name, **kwargs):
        if name not in self._factories:
            raise KeyError(f"unknown connector: {name}")
        return self._factories[name](**kwargs)

    def names(self):
        return tuple(sorted(self._factories))
