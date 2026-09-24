import asyncio
from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.utils.database import is_cleanmode, set_cleanmode

@app.on_message(filters.command(["cleanmode", "commanddelete"]) & filters.group)
async def cleanmode_toggle(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")

    if len(message.command) < 2:
        current = await is_cleanmode(message.chat.id)
        state_str = "Enabled" if current else "Disabled"
        return await message.reply_text(f"Command delete\n\n{state_str}")

    arg = message.command[1].lower()
    if arg in ["on", "enable", "true", "1"]:
        await set_cleanmode(message.chat.id, True)
        await message.reply_text("Command delete\n\nEnabled")
    elif arg in ["off", "disable", "false", "0"]:
        await set_cleanmode(message.chat.id, False)
        await message.reply_text("Command delete\n\nDisabled")
    else:
        current = await is_cleanmode(message.chat.id)
        state_str = "Enabled" if current else "Disabled"
        await message.reply_text(f"Command delete\n\n{state_str}")

async def auto_clean_message(msg: Message, delay: int = 180):
    """Background helper to delete command messages after a few minutes"""
    if await is_cleanmode(msg.chat.id):
        await asyncio.sleep(delay)
        try:
            await msg.delete()
        except Exception:
            pass
