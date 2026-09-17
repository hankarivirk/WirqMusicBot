from pyrogram import filters, types
from wirq import app, db

@app.on_message(filters.command(["broadcast"]) & app.sudoers)
async def _broadcast(_, m: types.Message):
    if not m.reply_to_message:
        return await m.reply_text("Reply to a message to broadcast it across chats.")
    sent = await m.reply_text("📢 Broadcasting message...")
    chats = await db.get_chats()
    success, failed = 0, 0
    for cid in chats:
        try:
            await m.reply_to_message.copy(cid)
            success += 1
        except Exception:
            failed += 1
    await sent.edit_text(f"✅ Broadcast finished. Sent: {success}, Failed: {failed}")
