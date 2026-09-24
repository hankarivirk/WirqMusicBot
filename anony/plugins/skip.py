from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.helpers._admins import is_admin
from anony.helpers._queue import Queues

@app.on_message(filters.command(["skip"]) & filters.group)
async def skip_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id
    if chat_id not in MusicCall.active_tracks:
        return await message.reply_text("No active voice chat found.")

    queue = Queues.get_queue(chat_id)
    if queue:
        await message.reply_text("Skipped.\n\nStarting the next track.")
    else:
        await message.reply_text("Skipped.\n\nNothing is waiting in the queue.")
    await MusicCall.on_song_end(chat_id)
