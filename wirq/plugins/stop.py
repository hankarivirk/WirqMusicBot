from pyrogram import filters, types
from wirq import anon, app, db, lang
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["end", "stop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _stop(_, m: types.Message):
    if not await db.get_call(m.chat.id):
        return await m.reply_text("Nothing is currently streaming in voice chat.")
    await anon.stop(m.chat.id)
    await m.reply_text(f"⏹ <b>Stream stopped and queue cleared</b> by {m.from_user.mention}.")
