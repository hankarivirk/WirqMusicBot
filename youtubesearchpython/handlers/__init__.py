class ComponentHandler:
    pass

def getValue(source, keys):
    if not source:
        return None
    for k in keys:
        if isinstance(source, dict):
            source = source.get(k)
        else:
            return None
    return source
