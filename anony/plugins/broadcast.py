from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config
from anony.utils.database import get_served_chats, get_served_users

@app.on_message(filters.command(["broadcast"]) & filters.user(config.OWNER_ID))
async def broadcast_command(_, message: Message):
    if not message.reply_to_message:
        return await message.reply_text("I don't recognize that action.\n\nOpen Help to see what I can do.")

    to_send = message.reply_to_message
    chats = await get_served_chats()
    sent = 0
    for chat_id in chats:
        try:
            await to_send.copy(chat_id)
            sent += 1
        except Exception:
            pass

    if sent > 0:
        await message.reply_text("Broadcast sent.")
    else:
        await message.reply_text("Broadcast couldn't be completed.")
