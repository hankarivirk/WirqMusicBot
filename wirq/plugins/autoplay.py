# Wirq Music Bot - Autoplay Plugin (Section 4)
from pyrogram import filters, types
from wirq import app, db, lang
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["autoplay"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _autoplay(_, m: types.Message):
    curr = await db.get_autoplay(m.chat.id)
    if len(m.command) < 2:
        new_state = not curr
    else:
        arg = m.command[1].lower()
        if arg in ["on", "enable", "true", "1"]:
            new_state = True
        elif arg in ["off", "disable", "false", "0"]:
            new_state = False
        else:
            return await m.reply_text("<b>Usage:</b> <code>/autoplay [on|off]</code>")

    await db.set_autoplay(m.chat.id, new_state)
    if new_state:
        msg = (
            "⚡ <b>Autoplay Enabled!</b>\\n"
            "When the queue finishes, the bot will automatically find and stream related YouTube tracks."
        )
    else:
        msg = (
            "⚡ <b>Autoplay Disabled!</b>\\n"
            "When the queue finishes, the bot will present 3 recommended YouTube songs with a '🔄 More' button."
        )
    await m.reply_text(msg)
