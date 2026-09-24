from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.utils.database import blacklist_chat, unblacklist_chat, blacklist_user, unblacklist_user, is_sudo

@app.on_message(filters.command(["blacklist", "block"]))
async def blacklist_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_sudo(user_id):
        return await message.reply_text("I don't have permission to do that here.")
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.id
        await blacklist_user(target)
        return await message.reply_text("User blocked.")
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
            if target < 0:
                await blacklist_chat(target)
            else:
                await blacklist_user(target)
            return await message.reply_text("User blocked.")
        except ValueError:
            pass
    await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")

@app.on_message(filters.command(["unblacklist", "unblock"]))
async def unblacklist_command(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if not await is_sudo(user_id):
        return await message.reply_text("I don't have permission to do that here.")
    target = None
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user.id
        await unblacklist_user(target)
        return await message.reply_text("User unblocked.")
    elif len(message.command) > 1:
        try:
            target = int(message.command[1])
            if target < 0:
                await unblacklist_chat(target)
            else:
                await unblacklist_user(target)
            return await message.reply_text("User unblocked.")
        except ValueError:
            pass
    await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")
