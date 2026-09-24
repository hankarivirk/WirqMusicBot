import os
import sys
from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.utils.database import is_sudo

@app.on_message(filters.command(["restart", "reboot"]))
async def restart_handler(_, message: Message):
    if not await is_sudo(message.from_user.id if message.from_user else 0):
        return
    await message.reply_text("⌁ Updating...")
    os.execl(sys.executable, sys.executable, "-m", "anony")
