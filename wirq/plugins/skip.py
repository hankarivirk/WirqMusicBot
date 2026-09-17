from pyrogram import filters, types
from wirq import anon, app, db, lang
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["skip", "next"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _skip(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text("Nothing is currently streaming in voice chat.")
    await anon.play_next(m.chat.id)
    await m.reply_text(f"⏭ <b>Skipped to next track</b> by {m.from_user.mention}.")
