from pyrogram import filters
from pyrogram.types import Message
from pyrogram.enums import ChatMemberStatus
from anony import app
from anony.helpers._admins import is_admin
from anony.utils.database import is_authuser, add_authuser, remove_authuser, get_authusers

@app.on_message(filters.command(["auth"]) & filters.group)
async def auth_handler(client, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")

    target_user = message.reply_to_message.from_user if message.reply_to_message else None
    target_id = target_user.id if target_user else int(message.command[1])

    try:
        member = await client.get_chat_member(message.chat.id, target_id)
        if member.status in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR]:
            return await message.reply_text("Access granted.")
    except Exception:
        pass

    await add_authuser(message.chat.id, target_id)
    await message.reply_text("Access granted.")

@app.on_message(filters.command(["unauth"]) & filters.group)
async def unauth_handler(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    if not message.reply_to_message and len(message.command) < 2:
        return await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")

    target_user = message.reply_to_message.from_user if message.reply_to_message else None
    target_id = target_user.id if target_user else int(message.command[1])

    await remove_authuser(message.chat.id, target_id)
    await message.reply_text("Access removed.")

@app.on_message(filters.command(["authusers"]) & filters.group)
async def authusers_list_handler(_, message: Message):
    users = await get_authusers(message.chat.id)
    if not users:
        return await message.reply_text("No authorized users found.")
    entries = "\n".join([f"• <code>{u}</code>" for u in users])
    await message.reply_text(f"Authorized users\n\n{entries}")
