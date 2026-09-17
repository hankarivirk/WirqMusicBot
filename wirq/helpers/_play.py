from functools import wraps
from pyrogram.types import Message
from wirq import config

def checkUB(func):
    @wraps(func)
    async def wrapper(_, m: Message, *args, **kwargs):
        from wirq import queue
        if len(queue.get_queue(m.chat.id)) >= config.QUEUE_LIMIT:
            return await m.reply_text(f"Queue is full (limit: {config.QUEUE_LIMIT}).")
        return await func(_, m, *args, **kwargs)
    return wrapper
