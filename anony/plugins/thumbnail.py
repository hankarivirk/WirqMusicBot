from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._admins import is_admin
from anony.helpers._inline import thumbnail_setting_markup
from anony.utils.database import get_thumbnail_setting, set_thumbnail_setting

@app.on_message(filters.command(["thumbnail", "thumbnails"]) & filters.group)
async def thumbnail_command(_, message: Message):
    if not await is_admin(message):
        return await message.reply_text("I need administrator access to control playback here.")
    chat_id = message.chat.id
    current = await get_thumbnail_setting(chat_id)

    if len(message.command) > 1:
        arg = message.command[1].strip().lower()
        if arg in ["on", "enable", "true", "1"]:
            await set_thumbnail_setting(chat_id, True)
            return await message.reply_text(
                "Group thumbnails\n\nEnabled",
                reply_markup=thumbnail_setting_markup(chat_id, True)
            )
        elif arg in ["off", "disable", "false", "0"]:
            await set_thumbnail_setting(chat_id, False)
            return await message.reply_text(
                "Group thumbnails\n\nDisabled",
                reply_markup=thumbnail_setting_markup(chat_id, False)
            )

    text = "Group thumbnails\n\nEnabled" if current else "Group thumbnails\n\nDisabled"
    await message.reply_text(text, reply_markup=thumbnail_setting_markup(chat_id, current))
