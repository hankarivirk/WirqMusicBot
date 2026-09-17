import os
import sys
from pyrogram import filters, types
from wirq import app

@app.on_message(filters.command(["restart"]) & app.sudoers)
async def _restart(_, m: types.Message):
    await m.reply_text("🔄 Restarting bot process...")
    os.execl(sys.executable, sys.executable, "-m", "wirq")
