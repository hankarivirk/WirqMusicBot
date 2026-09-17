from pyrogram import filters, types
from wirq import anon, app, db, lang
from wirq.helpers import buttons, can_manage_vc

@app.on_message(filters.command(["resume"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _resume(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text("Nothing is currently streaming in voice chat.")
    if await db.playing(m.chat.id):
        return await m.reply_text("Stream is not paused.")
    await anon.resume(m.chat.id)
    await m.reply_text(f"▶️ <b>Stream resumed</b> by {m.from_user.mention}.", reply_markup=buttons.controls(m.chat.id))
