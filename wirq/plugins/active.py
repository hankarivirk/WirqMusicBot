from pyrogram import filters, types
from wirq import app, db

@app.on_message(filters.command(["activevc", "ac"]) & app.sudoers)
async def _activevc(_, m: types.Message):
    calls = db.active_calls
    if not calls:
        return await m.reply_text("No active voice chat streams right now.")
    text = f"🔊 <b>Active Voice Chats ({len(calls)}):</b>\n\n"
    for i, chat_id in enumerate(calls.keys()):
        text += f"{i + 1}. <code>{chat_id}</code>\n"
    await m.reply_text(text)
