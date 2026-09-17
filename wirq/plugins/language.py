# Wirq Music Bot - Language Selection Plugin (Section 7)
from pyrogram import filters, types
from wirq import app, db, lang
from wirq.helpers import buttons

@app.on_message(filters.command(["lang", "language"]) & ~app.bl_users)
@lang.language()
async def _language(_, m: types.Message):
    if m.chat.type.value == "private":
        current = await db.get_user_lang(m.from_user.id)
        target = "your personal direct messages"
    else:
        current = await db.get_lang(m.chat.id)
        target = f"group <b>{m.chat.title}</b>"

    text = (
        f"🌐 <b>Language Settings:</b>\\n\\n"
        f"Currently selected for {target}: <code>{current.upper()}</code>\\n\\n"
        "<i>Select your preferred language below:</i>"
    )
    await m.reply_text(text, reply_markup=buttons.lang_markup(current))
