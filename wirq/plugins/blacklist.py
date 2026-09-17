from pyrogram import filters, types
from wirq import app, db

@app.on_message(filters.command(["blacklist"]) & app.sudoers)
async def _blacklist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text("Usage: <code>/blacklist [chat_id or user_id]</code>")
    try:
        target = int(m.command[1])
        await db.add_blacklist(target)
        await m.reply_text(f"🚫 Added <code>{target}</code> to blacklist.")
    except ValueError:
        await m.reply_text("Please provide a valid numeric ID.")

@app.on_message(filters.command(["unblacklist", "whitelist"]) & app.sudoers)
async def _unblacklist(_, m: types.Message):
    if len(m.command) < 2:
        return await m.reply_text("Usage: <code>/unblacklist [chat_id or user_id]</code>")
    try:
        target = int(m.command[1])
        await db.del_blacklist(target)
        await m.reply_text(f"✅ Removed <code>{target}</code> from blacklist.")
    except ValueError:
        await m.reply_text("Please provide a valid numeric ID.")
