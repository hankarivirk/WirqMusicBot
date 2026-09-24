import asyncio
from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config

@app.on_message(filters.command("updateytdl") & filters.user(config.OWNER_ID))
async def update_ytdl_cmd(_, message: Message):
    msg = await message.reply_text("Updating yt-dlp to latest release…")
    try:
        proc = await asyncio.create_subprocess_shell(
            "pip install -U yt-dlp",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate()
        out = stdout.decode().strip() or stderr.decode().strip()
        await msg.edit_text(f"yt-dlp updated.\n\n{out[-250:]}")
    except Exception as e:
        await msg.edit_text(f"Update failed: {e}")
