from pyrogram import filters, types
from wirq import app, db
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["auth"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _auth(_, m: types.Message):
    if not m.reply_to_message:
        return await m.reply_text("Reply to a user to authorize them to manage music.")
    user = m.reply_to_message.from_user
    await db.add_auth(m.chat.id, user.id)
    await m.reply_text(f"✅ Authorized {user.mention} to control music in this group.")

@app.on_message(filters.command(["unauth"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _unauth(_, m: types.Message):
    if not m.reply_to_message:
        return await m.reply_text("Reply to a user to revoke authorization.")
    user = m.reply_to_message.from_user
    await db.rm_auth(m.chat.id, user.id)
    await m.reply_text(f"❌ Revoked music authorization for {user.mention}.")
