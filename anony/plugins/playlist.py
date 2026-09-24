from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.plugins.play import play_handler

@app.on_message(filters.command(["playlist"]) & filters.group)
async def playlist_cmd_handler(client, message: Message):
    if len(message.command) < 2:
        return await message.reply_text("Type a song, artist, or album.")
    await play_handler(client, message)
