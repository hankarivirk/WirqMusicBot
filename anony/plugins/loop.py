from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.utils.database import get_loop, set_loop

@app.on_message(filters.command(["loop"]) & filters.group)
async def loop_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id
    current = await get_loop(chat_id)

    if len(message.command) < 2:
        if current > 0:
            await set_loop(chat_id, 0)
            return await message.reply_text("Loop disabled.")
        else:
            await set_loop(chat_id, 3)
            return await message.reply_text("Loop enabled.")

    arg = message.command[1].strip().lower()
    if arg in ["0", "off", "disable"]:
        await set_loop(chat_id, 0)
        return await message.reply_text("Loop disabled.")
    try:
        count = int(arg)
        if count > 0:
            await set_loop(chat_id, count)
            await message.reply_text("Loop enabled.")
        else:
            await set_loop(chat_id, 0)
            await message.reply_text("Loop disabled.")
    except ValueError:
        await message.reply_text("Loop enabled." if current > 0 else "Loop disabled.")
