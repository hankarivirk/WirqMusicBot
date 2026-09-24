from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.helpers._inline import autoplay_setting_markup
from anony.utils.database import is_autoplay, set_autoplay

@app.on_message(filters.command(["autoplay"]) & filters.group)
async def autoplay_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id
    current = await is_autoplay(chat_id)

    if len(message.command) > 1:
        arg = message.command[1].strip().lower()
        if arg in ["on", "enable", "true", "1"]:
            await set_autoplay(chat_id, True)
            return await message.reply_text(
                "Autoplay enabled.\n\nI'll keep the queue moving when it ends.",
                reply_markup=autoplay_setting_markup(chat_id, True)
            )
        elif arg in ["off", "disable", "false", "0"]:
            await set_autoplay(chat_id, False)
            return await message.reply_text(
                "Autoplay disabled.\n\nPlayback will stop when the queue ends.",
                reply_markup=autoplay_setting_markup(chat_id, False)
            )

    text = (
        "Autoplay enabled.\n\nI'll keep the queue moving when it ends."
        if current
        else "Autoplay disabled.\n\nPlayback will stop when the queue ends."
    )
    await message.reply_text(text, reply_markup=autoplay_setting_markup(chat_id, current))
