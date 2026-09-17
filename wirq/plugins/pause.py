from pyrogram import filters, types
from wirq import anon, app, db, lang
from wirq.helpers import buttons, can_manage_vc

@app.on_message(filters.command(["pause"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _pause(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text("Nothing is currently streaming in voice chat.")
    if not await db.playing(m.chat.id):
        return await m.reply_text("Stream is already paused.")
    await anon.pause(m.chat.id)
    await m.reply_text(f"⏸ <b>Stream paused</b> by {m.from_user.mention}.", reply_markup=buttons.controls(m.chat.id))
