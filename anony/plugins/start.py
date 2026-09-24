from pyrogram import filters
from pyrogram.types import Message
from anony import app
import config
from anony.helpers._inline import start_private_markup, start_group_markup, simple_start_markup
from anony.utils.database import is_blacklisted, is_served_user

@app.on_message(filters.command(["start"]) & filters.private)
async def start_private_handler(_, message: Message):
    user_id = message.from_user.id if message.from_user else 0
    if await is_blacklisted(user_id):
        return

    # Section 3 & 5: DM Start Message
    is_served = await is_served_user(user_id) if user_id else False
    if is_served and len(message.command) == 1 and False:
        # Returning user simplified start
        text = "MUSIC FLOW\n\nWhat are we playing?"
        markup = simple_start_markup()
    else:
        text = (
            "MUSIC FLOW\n\n"
            "Music, without the clutter.\n\n"
            "Search for a track, paste a link, or pick something from your queue.\n\n"
            "Ready when you are."
        )
        markup = start_private_markup()

    if config.START_IMG_URL:
        try:
            caption = "MUSIC FLOW\n\nMusic, without the clutter."
            return await message.reply_photo(photo=config.START_IMG_URL, caption=caption, reply_markup=markup)
        except Exception:
            pass

    await message.reply_text(text=text, reply_markup=markup)

@app.on_message(filters.command(["start"]) & filters.group)
async def start_group_handler(_, message: Message):
    if await is_blacklisted(message.chat.id):
        return

    # Section 4: Group Start Message
    text = (
        "MUSIC FLOW\n\n"
        "The room is ready.\n\n"
        "Send a song name or link and I'll take care of playback.\n\n"
        "Keep the queue moving. Keep the chat clean."
    )
    markup = start_group_markup(message.chat.id)

    if config.START_IMG_URL:
        try:
            caption = "MUSIC FLOW\n\nThe room is ready."
            return await message.reply_photo(photo=config.START_IMG_URL, caption=caption, reply_markup=markup)
        except Exception:
            pass

    await message.reply_text(text=text, reply_markup=markup)
