from pyrogram import filters, types
from wirq import anon, app, db, queue
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["seek"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _seek(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text("Nothing is currently streaming in voice chat.")
    if len(m.command) < 2 or not m.command[1].isdigit():
        return await m.reply_text("<b>Usage:</b> <code>/seek [seconds]</code>\nExample: <code>/seek 30</code>")
    seconds = int(m.command[1])
    current = queue.get_current(m.chat.id)
    if not current:
        return await m.reply_text("No track information available to seek.")
    if current.duration_sec and seconds > current.duration_sec:
        return await m.reply_text(f"⚠️ Cannot seek beyond track duration ({current.duration}).")
    sent = await m.reply_text(f"⏩ <b>Seeking to {seconds} seconds...</b>")
    await anon.play_media(m.chat.id, sent, current, seek_time=seconds)
