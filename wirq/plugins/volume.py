# Wirq Music Bot - Volume Control Plugin (Section 2)
from pyrogram import filters, types
from wirq import app, db, lang, calls
from wirq.helpers import can_manage_vc, buttons

@app.on_message(filters.command(["volume", "vol"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _volume(_, m: types.Message):
    curr_vol = await db.get_volume(m.chat.id)
    if len(m.command) < 2:
        return await m.reply_text(
            f"🔊 <b>Current Stream Volume:</b> <code>{curr_vol}%</code>\\n\\n"
            "Choose a volume preset below or set directly: <code>/volume &lt;1-100&gt;</code>",
            reply_markup=buttons.volume_markup(m.chat.id, curr_vol)
        )

    arg = m.command[1]
    if not arg.isdigit():
        return await m.reply_text("Please provide a number between 1 and 100.")

    vol = int(arg)
    if not (1 <= vol <= 100):
        return await m.reply_text("Volume must be between 1% and 100%.")

    success = await calls.volume(m.chat.id, vol)
    if success:
        await m.reply_text(f"🔊 <b>Stream volume set to {vol}%.</b>")
    else:
        await m.reply_text("❌ Failed to adjust volume. Ensure the voice chat is currently active.")
