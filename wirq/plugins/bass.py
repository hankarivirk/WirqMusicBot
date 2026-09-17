from pyrogram import filters, types
from wirq import app, db
from wirq.helpers import can_manage_vc

@app.on_message(filters.command(["bass"]) & filters.group & ~app.bl_users)
@can_manage_vc
async def _bass(_, m: types.Message):
    if len(m.command) < 2:
        curr = await db.get_bass(m.chat.id)
        return await m.reply_text(f"🔊 Current bass level: <b>{curr}dB</b>\nUsage: <code>/bass [0-20 or off]</code>")
    arg = m.command[1].lower()
    if arg in ["off", "disable", "0"]:
        await db.set_bass(m.chat.id, 0)
        return await m.reply_text("🔊 <b>Bass boost reset to default (0dB).</b>")
    if not arg.isdigit():
        return await m.reply_text("Please provide a number between 0 and 20.")
    level = min(max(int(arg), 0), 20)
    await db.set_bass(m.chat.id, level)
    await m.reply_text(f"🔊 <b>Hardware bass boost set to {level}dB.</b>")
