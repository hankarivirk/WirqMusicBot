from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.helpers._admins import is_admin

@app.on_message(filters.command(["stop"]) & filters.group)
async def stop_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id
    if chat_id not in MusicCall.active_tracks:
        return await message.reply_text("No active voice chat found.")

    await MusicCall.stop(chat_id)
    await message.reply_text("Playback stopped.\n\nQueue cleared.")
