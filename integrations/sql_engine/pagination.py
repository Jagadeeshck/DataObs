def bounded(items, maximum: int):
    for index, item in enumerate(items):
        if index >= maximum:
            return
        yield item
