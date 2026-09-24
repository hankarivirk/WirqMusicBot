from pyrogram import filters
from pyrogram.types import Message
from anony import app
from anony.helpers._inline import help_main_markup

@app.on_message(filters.command(["help"]))
async def help_command(_, message: Message):
    text = (
        "Help\n\n"
        "Everything you need, without the noise."
    )
    await message.reply_text(text=text, reply_markup=help_main_markup())

@app.on_message(filters.command(["about"]))
async def about_command(_, message: Message):
    text = (
        "MUSIC FLOW\n\n"
        "A clean music player for Telegram.\n\n"
        "Search. Play. Queue. Repeat.\n\n"
        "Keep the chat moving."
    )
    await message.reply_text(text=text)
