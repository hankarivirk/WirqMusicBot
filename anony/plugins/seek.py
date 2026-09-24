from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.helpers._admins import is_admin

@app.on_message(filters.command(["seek", "seekback"]) & filters.group)
async def seek_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("ADMIN REQUIRED\n\nYou do not have permission to manage playback in this chat.")
    chat_id = message.chat.id
    if chat_id not in MusicCall.active_tracks:
        return await message.reply_text("NOT PLAYING\n\nThere is no active stream in this chat.")

    cmd = message.command[0]
    if len(message.command) < 2:
        return await message.reply_text(
            f"USAGE\n\n"
            f"/{cmd} <seconds>\n\n"
            f"Example:\n\n"
            f"/{cmd} 15"
        )

    try:
        seconds = int(message.command[1])
    except ValueError:
        return await message.reply_text(
            f"USAGE\n\n"
            f"/{cmd} <seconds>"
        )

    if seconds < 10:
        return await message.reply_text("Minimum seek position is 10 seconds.")

    track = MusicCall.active_tracks[chat_id]
    dur_sec = track.get("duration_sec", 0)
    if dur_sec and seconds > dur_sec:
        return await message.reply_text(
            f"DURATION LIMIT\n\n"
            f"Streams longer than {dur_sec // 60} minutes are not allowed."
        )

    user_mention = message.from_user.mention if message.from_user else "Admin"
    status_msg = await message.reply_text("Seeking the current stream…")
    success = await MusicCall.seek(chat_id, seconds)
    try:
        await status_msg.delete()
    except Exception:
        pass
    if success:
        await message.reply_text(f"<b>Seeked by</b> {user_mention} to {seconds} seconds.")
    else:
        await message.reply_text("Failed to seek stream in voice chat.")
