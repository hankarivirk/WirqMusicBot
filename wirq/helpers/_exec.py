import traceback

def format_exception(e: Exception) -> str:
    return "".join(traceback.format_exception(type(e), e, e.__traceback__))

async def meval(code: str, local_vars: dict):
    return eval(code, globals(), local_vars)
