from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.helpers._inline import language_markup

@app.on_message(filters.command(["language", "lang"]))
async def language_command(_, message: Message):
    if message.chat.type != "private" and not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id if message.chat.type != "private" else 0
    await message.reply_text("Language\n\nChoose your language.", reply_markup=language_markup(chat_id))
