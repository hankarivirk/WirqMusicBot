from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.helpers._admins import is_admin

@app.on_message(filters.command(["vol", "volume"]) & filters.group)
async def volume_cmd(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    if len(message.command) < 2:
        return await message.reply_text("Volume level required (1-200).")

    vol = message.command[1]
    if not vol.isdigit():
        return await message.reply_text("Volume level required (1-200).")

    volume_level = int(vol)
    if not (1 <= volume_level <= 200):
        return await message.reply_text("Volume level required (1-200).")

    if not MusicCall.call:
        return await message.reply_text("No active voice chat found.")

    try:
        await MusicCall.call.change_volume_call(message.chat.id, volume_level)
        await message.reply_text(f"Volume set to {volume_level}%.")
    except Exception:
        await message.reply_text("No active voice chat found.")
