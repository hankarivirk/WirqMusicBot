from pyrogram.types import Message

class TelegramDownload:
    def __init__(self):
        pass

    async def download(self, message: Message) -> str:
        media = message.audio or message.video or message.document
        if not media:
            return None
        file_path = await message.download(file_name=f"downloads/{media.file_name or 'audio.mp3'}")
        return file_path

TG = TelegramDownload()
