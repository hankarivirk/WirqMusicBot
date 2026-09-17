from pyrogram import filters, types
from wirq import app

@app.on_message(filters.command(["sudoers"]) & app.sudoers)
async def _sudoers(_, m: types.Message):
    await m.reply_text(f"👑 <b>Bot Owner ID:</b> <code>{app.owner}</code>")
