class RequestCore:
    def __init__(self, *args, **kwargs):
        pass

    @staticmethod
    def buildInnertubeBody(client=None, query=None, videoId=None):
        return {
            "context": {"client": client or {"clientName": "WEB", "clientVersion": "2.20240101.00.00"}},
            "query": query or "",
        }

async def close_clients():
    pass

async def aclose_clients():
    pass
