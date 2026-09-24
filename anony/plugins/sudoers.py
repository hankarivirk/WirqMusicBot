from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config
from anony.utils.database import add_sudo, remove_sudo, is_sudo

@app.on_message(filters.command(["addsudo"]) & filters.user(config.OWNER_ID))
async def addsudo_command(_, message: Message):
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
        except ValueError:
            target = None
    if not target:
        return await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")
    await add_sudo(target)
    await message.reply_text("Access granted.")

@app.on_message(filters.command(["delsudo"]) & filters.user(config.OWNER_ID))
async def delsudo_command(_, message: Message):
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.id
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
        except ValueError:
            target = None
    if not target:
        return await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")
    await remove_sudo(target)
    await message.reply_text("Access removed.")
