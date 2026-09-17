import os
from pyrogram import types
from wirq import config, logger

class Telegram:
    def __init__(self):
        self.cancelled = set()

    def get_media(self, msg: types.Message) -> bool:
        return bool(msg and (msg.audio or msg.video or msg.document or msg.voice))

    async def cancel(self, query: types.CallbackQuery):
        self.cancelled.add(query.message.id)

    async def download(self, msg: types.Message, sent: types.Message) -> str | None:
        try:
            return await msg.download(file_name="downloads/")
        except Exception as e:
            logger.warning(f"Telegram media download error: {e}")
            return None

    async def process_m3u8(self, url: str, message_id: int, video: bool = False) -> str | None:
        return url
