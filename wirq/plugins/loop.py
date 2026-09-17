# Wirq Music Bot - 3-State Loop Control Plugin (Section 3)
from pyrogram import filters, types
from wirq import app, db, lang
from wirq.helpers import can_manage_vc

STATE_LABELS = {
    0: "Loop OFF (Queue advances normally)",
    1: "Loop Current Song (Repeats this track indefinitely)",
    2: "Loop Entire Queue (Cycles entire playlist endlessly)",
}

@app.on_message(filters.command(["loop"]) & filters.group & ~app.bl_users)
@lang.language()
@can_manage_vc
async def _loop(_, m: types.Message):
    curr = await db.get_loop(m.chat.id)
    if len(m.command) < 2:
        # Cycle through 3 states: 0 -> 1 -> 2 -> 0
        new_state = (curr + 1) % 3
        await db.set_loop(m.chat.id, new_state)
        return await m.reply_text(
            f"🔁 <b>Loop Mode Updated:</b>\\n<code>{STATE_LABELS[new_state]}</code>"
        )

    arg = m.command[1].lower()
    if arg in ["off", "disable", "0"]:
        new_state = 0
    elif arg in ["song", "track", "current", "1"]:
        new_state = 1
    elif arg in ["queue", "all", "playlist", "2"]:
        new_state = 2
    else:
        return await m.reply_text(
            "<b>Invalid argument.</b> Usage:\\n"
            "• <code>/loop</code> - Cycle next mode\\n"
            "• <code>/loop off</code> - Disable loop\\n"
            "• <code>/loop song</code> - Loop current song\\n"
            "• <code>/loop queue</code> - Loop entire playlist queue"
        )

    await db.set_loop(m.chat.id, new_state)
    await m.reply_text(f"🔁 <b>Loop Mode Set:</b>\\n<code>{STATE_LABELS[new_state]}</code>")
