# Wirq Music Bot - Queue & Shuffle Controls (Section 2)
from pyrogram import filters, types
from wirq import app, queue, lang, calls
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["queue", "cqueue"]) & filters.group & ~app.bl_users)
@lang.language()
async def _queue(_, m: types.Message):
    chat_id = m.chat.id
    current = queue.get_current(chat_id)
    items = queue.get_all(chat_id)

    if not current and not items:
        return await m.reply_text("📋 <b>The queue is currently empty.</b>")

    text = "📋 <b>Active Streaming Queue:</b>\\n\\n"
    if current:
        req = getattr(current, "user", "@wirq4")
        text += f"▶️ <b>Now Playing:</b> <a href='{current.url}'>{current.title}</a> ({current.duration})\\n👤 <i>Requested by: {req}</i>\\n\\n"

    if items:
        text += "<b>Upcoming Tracks:</b>\\n"
        for i, item in enumerate(items[:15], 1):
            req = getattr(item, "user", "@wirq4")
            text += f"<b>{i}.</b> <a href='{item.url}'>{item.title}</a> ({item.duration}) - <i>{req}</i>\\n"
        if len(items) > 15:
            text += f"\\n<i>...and {len(items) - 15} more tracks</i>"
    else:
        text += "<i>No upcoming tracks queued.</i>"

    await m.reply_text(
        text,
        disable_web_page_preview=True,
        reply_markup=types.InlineKeyboardMarkup([
            [
                types.InlineKeyboardButton("🔀 Shuffle", callback_data=f"controls shuffle {chat_id}"),
                types.InlineKeyboardButton("❌ Close", callback_data="close_btn")
            ]
        ])
    )

@app.on_message(filters.command(["clear", "clearqueue"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _clear(_, m: types.Message):
    await calls.clear(m.chat.id)
    await m.reply_text("🗑️ <b>Queue cleared successfully. Current track continues playing.</b>")

@app.on_message(filters.command(["shuffle"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _shuffle(_, m: types.Message):
    items = queue.get_all(m.chat.id)
    if not items or len(items) < 2:
        return await m.reply_text("Not enough tracks in queue to shuffle.")
    queue.shuffle(m.chat.id)
    await m.reply_text(f"🔀 <b>Successfully shuffled {len(items)} tracks in the queue!</b>")
