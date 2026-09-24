from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.core.calls import MusicCall
from anony.utils.database import is_sudo

@app.on_message(filters.command(["activevc", "activevoice", "ac"]))
async def active_vc_handler(_, message: Message):
    if not await is_sudo(message.from_user.id if message.from_user else 0):
        return
    active_chats = list(MusicCall.active_tracks.keys())
    if not active_chats:
        return await message.reply_text("No active streams.")

    lines = []
    for cid in active_chats:
        track = MusicCall.active_tracks.get(cid, {})
        lines.append(f"• <code>{cid}</code> | {track.get('title', 'Unknown')}")

    text = "Active streams\n\n" + "\n".join(lines)
    await message.reply_text(text)
